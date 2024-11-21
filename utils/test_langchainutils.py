# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch, MagicMock
from langchain_aws import ChatBedrock
import test_helper
test_helper.setup_path()
from utils.langchain_utils import LangChainUtils # pylint: disable=wrong-import-position

class TestLangChainUtils(unittest.TestCase):

    def test_get_chat_model_choices(self):
        """Test the `get_chat_model_choices` method."""
        choices = LangChainUtils.get_chat_model_choices()
        self.assertIsInstance(choices, dict)
        self.assertIn("Claude 3 Sonnet - Standard (Default)", choices)
        self.assertEqual(choices["Claude 3 Sonnet - Standard (Default)"]["model_id"],
                         "anthropic.claude-3-sonnet-20240229-v1:0")

    @patch('boto3.client')
    def test_get_chat_model_valid_choice(self, mock_boto_client):
        """Test the `get_chat_model` method with a valid model choice."""
        mock_bedrock_client = MagicMock()
        mock_boto_client.return_value = mock_bedrock_client

        chat = LangChainUtils.get_chat_model("Claude 3 Sonnet - Standard (Default)", region_name="us-west-2")
        self.assertIsInstance(chat, ChatBedrock)

    def test_get_chat_model_invalid_choice(self):
        """Test the `get_chat_model` method with an invalid model choice."""
        with self.assertRaises(ValueError):
            LangChainUtils.get_chat_model("Invalid Model Choice", region_name="us-west-2")

    @patch('boto3.client')
    def test_list_available_models_success(self, mock_boto_client):
        """Test the `list_available_models` method with mocked Bedrock response."""
        mock_bedrock_client = MagicMock()
        mock_boto_client.return_value = mock_bedrock_client
        mock_bedrock_client.list_foundation_models.return_value = {
            "modelSummaries": [
                {"modelId": "model-1", "modelName": "Model One", "providerName": "Provider A"},
                {"modelId": "model-2", "modelName": "Model Two", "providerName": "Provider B"},
            ]
        }

        with patch('builtins.print') as mock_print:
            LangChainUtils.list_available_models()
            mock_print.assert_any_call("Available models:")
            mock_print.assert_any_call("Model ID: model-1")
            mock_print.assert_any_call("Model ID: model-2")

    @patch('boto3.client')
    def test_list_available_models_failure(self, mock_boto_client):
        """Test the `list_available_models` method when an exception occurs."""
        mock_bedrock_client = MagicMock()
        mock_boto_client.return_value = mock_bedrock_client
        mock_bedrock_client.list_foundation_models.side_effect = Exception("Test Error")

        with patch('builtins.print') as mock_print:
            LangChainUtils.list_available_models()
            mock_print.assert_any_call("An error occurred: Test Error")

if __name__ == "__main__":
    unittest.main()
