# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch, MagicMock
import json
import toml
from botocore.exceptions import ClientError
from utils.config_store import ConfigStore

class TestConfigStore(unittest.TestCase):

    @patch('utils.config_store.boto3.client')
    def test_fetch_json_parameter(self, mock_boto3_client):
        # Mock the AWS response
        mock_client = MagicMock()
        mock_client.get_parameter.return_value = {
            'Parameter': {
                'Value': json.dumps({
                    "host": "database.example.com",
                    "user": "db_user",
                    "password": "securepassword"
                })
            }
        }
        mock_boto3_client.return_value = mock_client

        # Create the ConfigStore instance
        store = ConfigStore(default_path='/test/config')

        # Fetch the JSON parameter
        result = store['db']
        self.assertEqual(result['host'], "database.example.com")
        self.assertEqual(result['user'], "db_user")
        self.assertEqual(result['password'], "securepassword")

    @patch('utils.config_store.boto3.client')
    def test_fetch_toml_parameter(self, mock_boto3_client):
        # Mock the AWS response
        mock_client = MagicMock()
        mock_client.get_parameter.return_value = {
            'Parameter': {
                'Value': toml.dumps({
                    "saved_states": "data/saved_states",
                    "use_case_templates": "data/use_case_templates",
                    "templates_include_lib": "data/templates_include_lib"
                })
            }
        }
        mock_boto3_client.return_value = mock_client

        # Create the ConfigStore instance
        store = ConfigStore(default_path='/test/config')

        # Fetch the TOML parameter
        result = store['settings']
        self.assertEqual(result['saved_states'], "data/saved_states")
        self.assertEqual(result['use_case_templates'], "data/use_case_templates")
        self.assertEqual(result['templates_include_lib'], "data/templates_include_lib")

    @patch('utils.config_store.boto3.client')
    def test_parameter_not_found(self, mock_boto3_client):
        # Mock the AWS response to raise ParameterNotFound
        mock_client = MagicMock()


        mock_client.get_parameter.side_effect = ClientError(
            error_response={"Error":
                            {"Code": "ParameterNotFound", "Message": "Parameter not found"}
                    },
            operation_name="GetParameter"
        )
        mock_boto3_client.return_value = mock_client

        # Create the ConfigStore instance
        store = ConfigStore(default_path='/test/config')

        # Fetch a non-existent parameter
        result = store.get('nonexistent', default={"default_key": "default_value"})
        self.assertEqual(result, {"default_key": "default_value"})

    @patch('utils.config_store.boto3.client')
    def test_fetch_json_default_path(self, mock_boto3_client):
        # Mock the AWS response
        mock_client = MagicMock()
        mock_client.get_parameter.return_value = {
            'Parameter': {
                'Value': json.dumps({
                    "key": "value"
                })
            }
        }
        mock_boto3_client.return_value = mock_client

        # Test default path usage
        store = ConfigStore(env_var='TEST_ENV', default_path='/default/path')
        result = store['config']
        self.assertEqual(result['key'], "value")

    @patch('utils.config_store.boto3.client')
    def test_invalid_toml_format(self, mock_boto3_client):
        # Mock the AWS response with invalid TOML
        mock_client = MagicMock()
        mock_client.get_parameter.return_value = {
            'Parameter': {
                'Value': "not-a-valid-toml"
            }
        }
        mock_boto3_client.return_value = mock_client

        # Create the ConfigStore instance
        store = ConfigStore(default_path='/test/config')

        # Fetch the parameter and expect a parsing error
        with self.assertRaises(toml.TomlDecodeError):
            _settings = store['settings']

    @patch('utils.config_store.boto3.client')
    def test_invalid_json_format(self, mock_boto3_client):
        # Mock the AWS response with invalid JSON
        mock_client = MagicMock()
        mock_client.get_parameter.return_value = {
            'Parameter': {
                'Value': "{not-a-valid-json}"
            }
        }
        mock_boto3_client.return_value = mock_client

        # Create the ConfigStore instance
        store = ConfigStore(default_path='/test/config')

        # Fetch the parameter and expect a JSONDecodeError
        with self.assertRaises(json.JSONDecodeError):
            _db = store['db']


if __name__ == '__main__':
    unittest.main()
