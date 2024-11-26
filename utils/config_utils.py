""" Utility class to handle secure retrieval of params and secrets """
import os
import json
from functools import lru_cache
import logging
import hashlib
import boto3
from botocore.exceptions import ClientError
import toml
from utils.aws_utils import AWSUtils

class ConfigEnv:
    """ Exposes methods to get environment variables with defaults """

    @staticmethod
    def get_config_path() -> str:
        """ The location of the config """
        return os.getenv('CONFIG_PATH', 'local::default')

    @staticmethod
    def get_git_run_number() -> str:
        """ The GitHub run number of the build """
        return os.getenv('GIT_RUN_NUMBER', 'n/a')

    @staticmethod
    def get_git_commit_sha() -> str:
        """ The commit sha that triggered the build """
        return os.getenv('GIT_COMMIT_SHA', 'n/a')

class ConfigParamRetriever:
    """ Implements secure parameter retreival from configured location

    /*
    Configuration stored in AWS param store specied at container run time using CONFIG_PATH
    environment variable. Format is ssm::<base_key>

    There are some minimal configurations stored locally you can specify those of local::<config>
    */

    """
    local_config_dir = "local_data/configs"
    def __init__(self, config_path=None):
        """ Read enviroment variable for config location (if set), otherwise default """

        if config_path is None:
            self.config_path = ConfigEnv.get_config_path()
        else:
            self.config_path = config_path


    def get_local_configs(self):
        """ Returns the list of local configs available """
        # todo: use storage
        # Get path and check valid
        current_directory = os.getcwd()
        configs_path = os.path.join(current_directory, ConfigStore.local_config_dir)
        if not (os.path.exists(configs_path) or os.path.isdir(configs_path)):
            raise RuntimeError("The local configs directory does not exist")

        # Create a dictionary with folder names as keys and their full paths as values
        local_configs = {
            name: os.path.join(configs_path, name)
            for name in os.listdir(configs_path)
            if os.path.isdir(os.path.join(configs_path, name))
        }

        # Done
        return local_configs

    def __parse_section_helper(self, value):
        """ Parse the section value as JSON or TOML. """

        stripped_value = value.lstrip()
        if stripped_value.startswith("{"):
            # Parse as JSON
            ret_val = json.loads(value)
        else:
            # Parse as TOML
            ret_val = toml.loads(value)

        # Done
        return ret_val

    @lru_cache(maxsize=10)
    def _fetch_section_from_local(self, key):
        """ Read a config section from local storage """
        # Match agaisnt local list rather than use path directly as that is not secure
        config_path = self.config_path.removeprefix("local::")
        local_configs = self.get_local_configs()
        if config_path not in local_configs:
            err_msg = f"The local config '{config_path}' does not exist"
            raise KeyError(err_msg)

        def read_local_section():
            """ Reads the file with .json or .toml extension """
            file_extensions = [".json", ".toml"]
            for ext in file_extensions:

                # Check if the file exists
                file_path = os.path.join(local_configs[config_path], f"{key}{ext}")
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as file:
                        return file.read()

            # If neither file is found, raise an error
            err_msg = f"Neither '{key}.json' nor '{key}.toml' exists."
            raise FileNotFoundError(err_msg)

        # Read, parse and return
        content = read_local_section()
        content = self.__parse_section_helper(content)
        return content


    def _fetch_section_from_ssm_param(self, key):
        """ Read a config section from AWS SSM param storage """

        config_path = self.config_path.removeprefix("ssm::")
        parameter_name = f"{config_path}/{key}"
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        parameter_value = response['Parameter']['Value']
        return self.__parse_section_helper(parameter_value)

    def _fetch_section(self, key):
        """ Fetch a config section from the store """

        # Check if its a local config
        if self.config_path.startswith('local::'):
            return self._fetch_section_from_local(key)

        # Default to ssm config
        return self._fetch_section_from_ssm_param(key)

    def __getitem__(self, key):
        """ Access a parameter like a dictionary. """
        return self._fetch_section(key)

    def get(self, key, default=None):
        """  Get a parameter value with a default. """
        try:
            return self._fetch_section(key)
        except ClientError:
            return default

    @classmethod
    def nested_get(cls, # pylint: disable=too-many-arguments, too-many-locals
                   nested_key,
                   default_value=None,
                   default_log_msg='',
                   config_path=None):
        """
        Retrieve a nested config value using dot notation.

        Parameters:
            nested_key (str): The dotted path to the key representing the value
            default_value (Any, optional): The value to return if the specified key cannot be found.
            default_log_msg (str, optional): A message to log when the default value is returned.
            config_path (str, optional): The configuration path if different from default

        Returns:
            Any: The value requested, or the default value if the key is not found.
            Will raise an exception if value cannot be found and default not specified

        """

        def default_logging_warning():
            """ helper to log a warning message if default used"""
            if default_log_msg is not None:
                msg = f"Defaulting '{nested_key}' to '{default_value}'. {default_log_msg}"
                logging.warning(msg)

        try:
            # Initialize ConfigStore instance to fetch parameters
            instance = cls(config_path=config_path)
            keys = nested_key.split('.')

            # Recursively fetch nested keys
            def recursive_get(keys, value):
                if not keys:
                    return value
                current_key = keys[0]
                if isinstance(value, dict):
                    return recursive_get(keys[1:], value[current_key])

                # Not found
                raise KeyError(f"Key '{current_key}' not found in nested structure.")

            # Retrieve the first level parameter
            top_level_key = keys[0]
            path_in_dict = keys[1:]
            top_level_value = instance[top_level_key]

            # Perform recursive lookup
            return recursive_get(path_in_dict, top_level_value)
        except ClientError as exc:

            # Handle safely if we have default
            if default_value is not None:
                default_logging_warning()
                return default_value

            # Raise error as not handled
            raise ValueError(f"Unable to retrieve parameter from AWS SSM: {exc}") from exc
        except (KeyError, TypeError) as exc:

            # Handle safely if we have default
            if default_value is not None:
                default_logging_warning()
                return default_value

            # Raise error as not handled
            param_path = f"{instance.config_path}/{top_level_key}"
            path_in_dict_str = '.'.join(path_in_dict)
            err_msg = f"Unable to find '{path_in_dict_str}' in data at '{param_path}': {exc}"
            exc.args = (f"{err_msg}. Original error: {exc}",) + exc.args[1:]
            raise

class ConfigStore(ConfigParamRetriever):
    """ Handles all config related functions on top of retrieval """

    @staticmethod
    def generate_friendly_name(commit_ref: str) -> str:
        """ Generate a friendly name for a Git commit reference. """

        adjectives = [
            "heavenly", "bright", "calm", "daring", "elegant",
            "fierce", "gentle", "happy", "jovial", "kind",
            "lively", "mighty", "noble", "peaceful", "quiet",
            "radiant", "strong", "trusty", "unique", "vivid",
            "witty", "zesty", "brilliant", "cheerful", "bold",
            "courageous", "playful", "charming", "fanciful", "heroic",
            "thoughtful", "spirited", "graceful", "fearless", "quirky",
            "humble", "resilient", "joyful", "marvelous", "proud"
        ]

        nouns = [
            "tomatoes", "sunrise", "forest", "ocean", "mountains",
            "skyline", "rivers", "butterflies", "galaxies", "flowers",
            "thunder", "stars", "lions", "panthers", "wolves",
            "phoenix", "dolphins", "dragons", "sparrows", "tigers",
            "eagles", "unicorns", "horizons", "prairies", "sandstorms",
            "avalanches", "waterfalls", "orchids", "plains", "meteors",
            "lightning", "foxes", "comets", "jungles", "crystals",
            "sequoias", "snowflakes", "whales", "peacocks", "embers"
        ]

        # Hash the commit reference to generate a deterministic value
        hash_value = hashlib.sha256(commit_ref.encode()).hexdigest()

        # Convert hash to integers for indexing
        adjective_index = int(hash_value[:8], 16) % len(adjectives)
        noun_index = int(hash_value[8:16], 16) % len(nouns)

        # Select adjective and noun based on hashed indices
        adjective = adjectives[adjective_index]
        noun = nouns[noun_index]

        # Return the friendly name
        return f"{adjective}-{noun}"

    @staticmethod
    def get_config_status_string():
        """ Return a string summarising the config status """

        config_path = ConfigEnv.get_config_path()
        git_commit_sha = ConfigEnv.get_git_commit_sha()
        git_run_number = ConfigEnv.get_git_run_number()
        friendly_name = ConfigStore.generate_friendly_name(git_commit_sha)

        _aws_configured, aws_status = AWSUtils.is_aws_configured()
        status_string =  f'BUILD: {friendly_name}-{git_run_number}, CONFIG: {config_path}, AWS: {aws_status}'
        return status_string
