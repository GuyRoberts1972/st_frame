# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch, MagicMock
import json
import toml
from botocore.exceptions import ClientError
from utils.config_utils import ConfigStore


class TestConfigStoreLocalStorage(unittest.TestCase):

    def test_local_default_confg(self):

        # Happy path
        templates_include_lib = ConfigStore.nested_get(
            'paths.templates_include_lib',
            default_config_path='local::default',
            env_var=None)
        self.assertEqual(templates_include_lib, 'local_data/data/templates_include_lib')

        # invalid key
        with self.assertRaises(KeyError):
            ConfigStore.nested_get(
                'paths.idonotexist',
                default_config_path='local::default',
                env_var=None)

        # invalid section
        with self.assertRaises(FileNotFoundError):
            ConfigStore.nested_get(
                'neitherdoi.idonotexist',
                default_config_path='local::default',
                env_var=None)

        # Invalid local storage
        with self.assertRaises(KeyError):
            ConfigStore.nested_get(
                'mute',
                default_config_path='local::bad',
                env_var=None)


class TestConfigStoreAWSSSM(unittest.TestCase):

    @patch('utils.config_utils.boto3.client')
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
        store = ConfigStore(default_path='ssm::/test/config')

        # Fetch the JSON parameter
        result = store['db']
        self.assertEqual(result['host'], "database.example.com")
        self.assertEqual(result['user'], "db_user")
        self.assertEqual(result['password'], "securepassword")

    @patch('utils.config_utils.boto3.client')
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
        store = ConfigStore(default_path='ssm::/test/config')

        # Fetch the TOML parameter
        result = store['settings']
        self.assertEqual(result['saved_states'], "data/saved_states")
        self.assertEqual(result['use_case_templates'], "data/use_case_templates")
        self.assertEqual(result['templates_include_lib'], "data/templates_include_lib")

    @patch('utils.config_utils.boto3.client')
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
        store = ConfigStore(default_path='ssm::/test/config')

        # Fetch a non-existent parameter
        result = store.get('nonexistent', default={"default_key": "default_value"})
        self.assertEqual(result, {"default_key": "default_value"})

    @patch('utils.config_utils.boto3.client')
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

    @patch('utils.config_utils.boto3.client')
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
        store = ConfigStore(default_path='ssm::/test/config')

        # Fetch the parameter and expect a parsing error
        with self.assertRaises(toml.TomlDecodeError):
            _settings = store['settings']

    @patch('utils.config_utils.boto3.client')
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
        store = ConfigStore(default_path='ssm::/test/config')

        # Fetch the parameter and expect a JSONDecodeError
        with self.assertRaises(json.JSONDecodeError):
            _db = store['db']

class TestConfigStoreNestedGet(unittest.TestCase):

    @patch.object(ConfigStore, '_fetch_section')
    def test_nested_get_success(self, mock_fetch_section):
        """ Test nested_get successfully retrieves a deeply nested value. """
        # Mock the return value for the top-level parameter 'paths'
        mock_fetch_section.return_value = {
            'templates_include_lib': {
                'subkey': 'value'
            }
        }

        # Call nested_get
        value = ConfigStore.nested_get('paths.templates_include_lib.subkey')

        # Assert the correct value
        self.assertEqual(value, 'value')

    @patch.object(ConfigStore, '_fetch_section')
    def test_nested_get_key_not_found(self, mock_fetch_section):
        """ Test nested_get raises an exception when a key is not found. """
        # Mock the return value for the top-level parameter 'paths'
        mock_fetch_section.return_value = {
            'templates_include_lib': {}
        }

        # Expect an exception when accessing a non-existent key
        with self.assertRaises(KeyError) as _context:
            ConfigStore.nested_get('paths.templates_include_lib.nonexistent_key')


    @patch.object(ConfigStore, '_fetch_section')
    def test_nested_get_with_default(self, mock_fetch_section):
        """ Test nested_get returns default value if key is not found. """
        # Mock the return value for the top-level parameter 'paths'
        mock_fetch_section.return_value = {
            'templates_include_lib': {}
        }

        # Call nested_get with a default value
        value = ConfigStore.nested_get('paths.templates_include_lib.nonexistent_key',
                                       default_value='default_value',
                                       default_log_msg='needed to default key that did not exists')

        # Assert default is returned
        self.assertEqual(value, 'default_value')

    @patch.object(ConfigStore, '_fetch_section')
    def test_nested_get_invalid_type(self, mock_fetch_section):
        """ Test nested_get raises an exception for invalid type in the path. """
        # Mock the return value for the top-level parameter 'paths'
        mock_fetch_section.return_value = {
            'templates_include_lib': 'not_a_dict'
        }

        # Expect an exception when traversing into a non-dict type
        with self.assertRaises(KeyError) as _context:
            ConfigStore.nested_get('paths.templates_include_lib.subkey')


if __name__ == '__main__':
    unittest.main()
