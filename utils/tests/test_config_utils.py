# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch, MagicMock
import json
import tempfile
import os
import logging
import toml
from botocore.exceptions import ClientError
from utils.config_utils import ConfigStore, VersionInfo


class TestConfigStoreLocalStorage(unittest.TestCase):

    def test_local_default_confg(self):

        # Happy path
        templates_include_lib = ConfigStore.nested_get(
            'paths.templates_include_lib',
            config_path='local::default')
        self.assertEqual(templates_include_lib, 'local_data/data/templates_include_lib')

        # invalid key
        with self.assertRaises(KeyError):
            ConfigStore.nested_get(
                'paths.idonotexist',
                config_path='local::default'
                )

        # invalid section
        with self.assertRaises(FileNotFoundError):
            ConfigStore.nested_get(
                'neitherdoi.idonotexist',
                config_path='local::default'
                )

        # Invalid local storage
        with self.assertRaises(KeyError):
            ConfigStore.nested_get(
                'mute',
                config_path='local::bad'
                )

class TestVersionInfo(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.toml_path = os.path.join(self.temp_dir, 'version_info.toml')
        self.test_data = {
            'build': {
                'github_run_number': '123',
                'github_ref': 'refs/heads/main',
                'github_sha': 'abcdef1234567890'
            }
        }
        with open(self.toml_path, 'w', encoding='utf-8') as f:
            toml.dump(self.test_data, f)

    def tearDown(self):
        os.remove(self.toml_path)
        os.rmdir(self.temp_dir)

    def test_load_toml(self):
        version_info = VersionInfo(self.toml_path)
        self.assertEqual(version_info.config, self.test_data)

    def test_get_github_run_number(self):
        version_info = VersionInfo(self.toml_path)
        self.assertEqual(version_info.get_github_run_number(), '123')

    def test_get_github_ref(self):
        version_info = VersionInfo(self.toml_path)
        self.assertEqual(version_info.get_github_ref(), 'refs/heads/main')

    def test_get_github_sha(self):
        version_info = VersionInfo(self.toml_path)
        self.assertEqual(version_info.get_github_sha(), 'abcdef1234567890')

    def test_file_not_found(self):
        with self.assertLogs(level='WARNING') as cm:
            version_info = VersionInfo('non_existent_file.toml')

        self.assertEqual(version_info.get_github_run_number(), 'n/a')

class TestConfigStore(unittest.TestCase):
    @patch.dict(os.environ, {'CONFIG_PATH': 'local::test'})
    def test_get_config_path_from_env(self):
        self.assertEqual(ConfigStore.get_config_path_from_env(), 'local::test')

    @patch('utils.config_utils.ConfigStore._fetch_section_from_local')
    def test_fetch_section_local(self, mock_fetch):
        mock_fetch.return_value = {'key': 'value'}
        config_store = ConfigStore('local::test')
        result = config_store['test_section']
        self.assertEqual(result, {'key': 'value'})
        mock_fetch.assert_called_once_with('test_section')

    @patch('utils.config_utils.ConfigStore._fetch_section_from_ssm_param')
    def test_fetch_section_ssm(self, mock_fetch):
        mock_fetch.return_value = {'key': 'value'}
        config_store = ConfigStore('ssm::test')
        result = config_store['test_section']
        self.assertEqual(result, {'key': 'value'})
        mock_fetch.assert_called_once_with('test_section')

    @patch('utils.config_utils.ConfigStore._fetch_section')
    def test_get_with_default(self, mock_fetch):
        # Create a ClientError exception
        error_response = {'Error': {'Code': 'ParameterNotFound', 'Message': 'Parameter not found.'}}
        mock_fetch.side_effect = ClientError(error_response, 'GetParameter')

        config_store = ConfigStore()
        result = config_store.get('non_existent', default='default_value')
        self.assertEqual(result, 'default_value')

    @patch('utils.config_utils.ConfigStore._fetch_section')
    def test_nested_get(self, mock_fetch):
        mock_fetch.return_value = {'nested': {'key': 'value'}}
        result = ConfigStore.nested_get('section.nested.key')
        self.assertEqual(result, 'value')

    def test_generate_friendly_name(self):
        name1 = ConfigStore.generate_friendly_name('commit1')
        name2 = ConfigStore.generate_friendly_name('commit2')
        self.assertNotEqual(name1, name2)
        self.assertRegex(name1, r'^[a-z]+-[a-z]+$')
        self.assertRegex(name2, r'^[a-z]+-[a-z]+$')

    @patch('utils.config_utils.VersionInfo')
    @patch('utils.config_utils.AWSUtils.is_aws_configured')
    def test_get_config_and_version_string(self, mock_aws, mock_version_info):
        mock_version_info.return_value.get_github_ref.return_value = 'main'
        mock_version_info.return_value.get_github_sha.return_value = 'abcdef'
        mock_version_info.return_value.get_github_run_number.return_value = '123'
        mock_aws.return_value = (True, 'Configured')

        with patch.dict(os.environ, {'CONFIG_PATH': 'local::test'}):
            result = ConfigStore.get_config_and_version_string()

        self.assertIn('SHA:', result)
        self.assertIn('RUN: 123', result)
        self.assertIn('REF: main', result)
        self.assertIn('CONFIG: local::test', result)
        self.assertIn('AWS: Configured', result)

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
        store = ConfigStore(config_path='ssm::/test/config')

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
        store = ConfigStore(config_path='ssm::/test/config')

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
        store = ConfigStore(config_path='ssm::/test/config')

        # Fetch a non-existent parameter
        result = store.get('nonexistent', default={"default_key": "default_value"})
        self.assertEqual(result, {"default_key": "default_value"})

    @patch('utils.config_utils.boto3.client')
    def test_fetch_json_config_path(self, mock_boto3_client):
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
        store = ConfigStore(config_path='/default/path')
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
        store = ConfigStore(config_path='ssm::/test/config')

        # Fetch the parameter and expect a parsing error
        with self.assertRaises(ValueError):
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
        store = ConfigStore(config_path='ssm::/test/config')

        # Fetch the parameter and expect a ValueError
        with self.assertRaises(ValueError):
            _db = store['db']



class TestConfigStoreNestedGet(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.ERROR)  # Disable all logging

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)  # Re-enable logging

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
