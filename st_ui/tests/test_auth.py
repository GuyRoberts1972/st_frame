# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch
from utils.config_utils import ConfigStore
from st_ui.auth import AuthBase, NoneAuth, BasicAuth, IAPAuth
class TestAuthBase(unittest.TestCase):

    def test_get_auth_object_none(self):
        with patch.object(ConfigStore, 'nested_get', return_value='none'):
            auth = AuthBase._get_auth_object()
            self.assertIsInstance(auth, NoneAuth)

    def test_get_auth_object_basic(self):
        with patch.object(ConfigStore, 'nested_get', return_value='basic'):
            auth = AuthBase._get_auth_object()
            self.assertIsInstance(auth, BasicAuth)

    @patch('st_ui.auth._get_websocket_headers')
    def test_get_auth_object_iap(self, mock_get_headers):
        mock_get_headers.return_value = {'X-User': 'test_user'}
        with patch.object(ConfigStore, 'nested_get', return_value='iap'):
            auth = AuthBase._get_auth_object()
            self.assertIsInstance(auth, IAPAuth)

    def test_get_auth_object_invalid(self):
        with patch.object(ConfigStore, 'nested_get', return_value='invalid'):
            with self.assertRaises(ValueError):
                AuthBase._get_auth_object()

class TestNoneAuth(unittest.TestCase):

    def setUp(self):
        self.auth = NoneAuth()

    def test_is_authorized(self):
        self.assertTrue(self.auth.is_authorized())

    def test_get_username(self):
        self.assertEqual(self.auth.get_username(), "Guest")

class TestIAPAuth(unittest.TestCase):

    @patch.object(ConfigStore, 'nested_get', return_value='X-User')
    @patch('st_ui.auth._get_websocket_headers')
    def test_init_with_valid_header(self, mock_get_headers, mock_config):
        mock_get_headers.return_value = {'X-User': 'test_user'}
        auth = IAPAuth()
        self.assertEqual(auth.username, 'test_user')

    @patch.object(ConfigStore, 'nested_get', return_value=None)
    def test_init_with_missing_config(self, mock_config):
        with self.assertRaises(ValueError):
            IAPAuth()

class TestBasicAuth(unittest.TestCase):

    @patch.object(ConfigStore, 'nested_get')
    def setUp(self, mock_config):
        mock_config.return_value = {
            'user1': BasicAuth.generate_password_hash('password1'),
            'user2': BasicAuth.generate_password_hash('password2')
        }
        self.auth = BasicAuth()

    def test_is_authorized_initial(self):
        self.assertFalse(self.auth.is_authorized())

    def test_get_username_initial(self):
        self.assertIsNone(self.auth.get_username())

    @patch('streamlit.text_input')
    @patch('streamlit.button')
    def test_login_prompt_success(self, mock_button, mock_text_input):
        mock_text_input.side_effect = ['user1', 'password1']
        mock_button.return_value = True

        self.auth.login_prompt()

        self.assertTrue(self.auth.is_authorized())
        self.assertEqual(self.auth.get_username(), 'user1')

    @patch('streamlit.text_input')
    @patch('streamlit.button')
    def test_login_prompt_failure(self, mock_button, mock_text_input):
        mock_text_input.side_effect = ['user1', 'wrong_password']
        mock_button.return_value = True

        self.auth.login_prompt()

        self.assertFalse(self.auth.is_authorized())
        self.assertIsNone(self.auth.get_username())

if __name__ == "__main__":
    unittest.main()
