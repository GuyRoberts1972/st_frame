# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch, MagicMock
from langchain_aws import ChatBedrock
from utils.langchain_utils import LangChainUtils, InternalStubModel

class TestLangChainUtils(unittest.TestCase):

    @patch('utils.aws_utils.AWSUtils.is_aws_configured')
    def test_get_chat_model_choices(self, mock_is_aws_configured):
        """Test the `get_chat_model_choices` method."""
        mock_is_aws_configured.return_value = True, 'mocked reason'
        choices = LangChainUtils.get_chat_model_choices()
        self.assertIsInstance(choices, dict)
        self.assertIn("Claude 3 Sonnet - Standard (Default)", choices)
        self.assertEqual(choices["Claude 3 Sonnet - Standard (Default)"]["model_id"],
                         "anthropic.claude-3-sonnet-20240229-v1:0")


    def test_get_chat_model_valid_choice(self):
        """Test the `get_chat_model` method with a valid model choice."""

        chat = LangChainUtils.get_chat_model("Mock Model - Echo")
        self.assertIsInstance(chat, InternalStubModel)

    def test_get_chat_model_invalid_choice(self):
        """Test the `get_chat_model` method with an invalid model choice."""
        with self.assertRaises(ValueError):
            LangChainUtils.get_chat_model("Invalid Model Choice", region_name="us-west-2")

    @patch('boto3.client')
    def test_print_available_aws_bedrock_models_success(self, mock_boto_client):
        """Test the `print_available_aws_bedrock_models` method with mocked Bedrock response."""
        mock_bedrock_client = MagicMock()
        mock_boto_client.return_value = mock_bedrock_client
        mock_bedrock_client.list_foundation_models.return_value = {
            "modelSummaries": [
                {"modelId": "model-1", "modelName": "Model One", "providerName": "Provider A"},
                {"modelId": "model-2", "modelName": "Model Two", "providerName": "Provider B"},
            ]
        }

        with patch('builtins.print') as mock_print:
            LangChainUtils.print_available_aws_bedrock_models()
            mock_print.assert_any_call("Available models:")
            mock_print.assert_any_call("Model ID: model-1")
            mock_print.assert_any_call("Model ID: model-2")

    def test_simple_prompt_response_with_stub_model(self):
        """Test simple_prompt_response with an internal stub model."""

        initial_system_prompt = "This is a system prompt."
        human_prompt = "Hello, how are you?"

        # Call the simple_prompt_response method
        response = LangChainUtils.simple_prompt_response(
            chat_model=LangChainUtils.get_chat_model("Mock Model - Echo"),
            initial_system_prompt=initial_system_prompt,
            human_prompt=human_prompt
        )

        # Assert the response matches the human prompt (echo behavior)
        self.assertEqual(response, human_prompt)

    def test_chat_prompt_response_with_stub_model(self):
        """Test chat_prompt_response with an internal stub model."""

        initial_system_prompt = "This is a system prompt."
        human_prompt = "Tell me something interesting."
        prior_chat_history = [
            {"role": "user", "content": "Hi!"},
            {"role": "assistant", "content": "Hello! How can I help you?"}
        ]

        # Call the chat_prompt_response method
        response = LangChainUtils.chat_prompt_response(
            chat_model=LangChainUtils.get_chat_model("Mock Model - Echo"),
            initial_system_prompt=initial_system_prompt,
            human_prompt=human_prompt,
            prior_chat_history=prior_chat_history
        )

        # Assert the response matches the human prompt (echo behavior)
        self.assertEqual(response, human_prompt)

if __name__ == "__main__":
    unittest.main()
