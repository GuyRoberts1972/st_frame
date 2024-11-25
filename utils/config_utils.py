""" Utility class to handle secure retrieval of params and secrets """
import os
import json
from functools import lru_cache
import logging
import boto3
from botocore.exceptions import ClientError
import toml

class ConfigStore:
    """ Impements secure parameter retreival from configured location

    [configstore.summary]
    Configuration stored in AWS param store specied at container run time using CONFIG_STORE_PATH
    environment variable. Format is ssm::<base_key>

    There are some minimal configurtions stored locally you can specify those of local::<config>

    """
    local_config_dir = "local_data/configs"
    def __init__(self, default_path='local::default', env_var='CONFIG_STORE_PATH'):
        """ Read enviroment variable for config location (if set), otherwise default """

        if env_var:
            self.base_path = os.getenv(env_var, default_path)
        else:
            self.base_path  = default_path

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
        base_path = self.base_path.removeprefix("local::")
        local_configs = self.get_local_configs()
        if base_path not in local_configs:
            err_msg = f"The local config '{base_path}' does not exist"
            raise KeyError(err_msg)

        def read_local_section():
            """ Reads the file with .json or .toml extension """
            file_extensions = [".json", ".toml"]
            for ext in file_extensions:

                # Check if the file exists
                file_path = os.path.join(local_configs[base_path], f"{key}{ext}")
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

        base_path = self.base_path.removeprefix("ssm::")
        parameter_name = f"{base_path}/{key}"
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        parameter_value = response['Parameter']['Value']
        return self.__parse_section_helper(parameter_value)

    def _fetch_section(self, key):
        """ Fetch a config section from the store """

        # Check if its a local config
        if self.base_path.startswith('local::'):
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
                   default_config_path='local::default',
                   env_var='CONFIG_STORE_PATH'):
        """
        Retrieve a nested config value using dot notation.

        Parameters:
            nested_key (str): The dotted path to the key representing the value
            default_value (Any, optional): The value to return if the specified key cannot be found.
            default_log_msg (str, optional): A message to log when the default value is returned.
            default_config_path (str, optional): The configuration path if not via the env variable.
            env_var (str, optional): The env variable to check for the configuration path.

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
            instance = cls(default_path=default_config_path, env_var=env_var)
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
            param_path = f"{instance.base_path}/{top_level_key}"
            path_in_dict_str = '.'.join(path_in_dict)
            err_msg = f"Unable to find '{path_in_dict_str}' in data at '{param_path}': {exc}"
            exc.args = (f"{err_msg}. Original error: {exc}",) + exc.args[1:]
            raise
