""" Utility class to handle secure retrieval of params and secrets """
import os
import json
import boto3
from botocore.exceptions import ClientError
import toml

class ConfigStore:
    """ Impements secure parameter retreival from configured location """
    def __init__(self, env_var='PARAM_STORE_PATH', default_path='/st_frame/config'):
        """ Initialize ConfigStore. """

        self.base_path = os.getenv(env_var, default_path)
        self.client = boto3.client('ssm')

    def _fetch_parameter(self, key):
        """ Fetch a single parameter from AWS Parameter Store. """

        parameter_name = f"{self.base_path}/{key}"
        response = self.client.get_parameter(Name=parameter_name, WithDecryption=True)
        parameter_value = response['Parameter']['Value']
        return self._parse_parameter(parameter_value)

    def _parse_parameter(self, value):
        """ Parse the parameter value as JSON or TOML. """

        stripped_value = value.lstrip()
        if stripped_value.startswith("{"):
            # Parse as JSON
            return json.loads(value)
        else:
            # Parse as TOML
            return toml.loads(value)

    def __getitem__(self, key):
        """ Access a parameter like a dictionary. """
        return self._fetch_parameter(key)

    def get(self, key, default=None):
        """  Get a parameter value with a default. """
        try:
            return self._fetch_parameter(key)
        except ClientError:
            return default

