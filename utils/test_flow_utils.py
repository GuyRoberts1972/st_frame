# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch
from utils.flow_utils import FlowUtils


class TestURLExtraction(unittest.TestCase):

    def test_simple_url(self):
        text = "Visit our website at https://www.example.com for more information."
        self.assertEqual(FlowUtils.extract_urls_from_text(text), ['https://www.example.com'])

    def test_multiple_urls(self):
        text = "Check out http://site1.com and https://site2.org for great content!"
        self.assertEqual(
            FlowUtils.extract_urls_from_text(text),
            ['http://site1.com', 'https://site2.org'])

    def test_url_with_path(self):
        text = "Article link: https://blog.example.com/articles/2023/05/15/ai-advancements"
        self.assertEqual(
            FlowUtils.extract_urls_from_text(text),
            ['https://blog.example.com/articles/2023/05/15/ai-advancements'])

    def test_url_with_query_params(self):
        text = "Search results: https://search.example.com/results?q=python&page=1"
        self.assertEqual(
            FlowUtils.extract_urls_from_text(text),
            ['https://search.example.com/results?q=python&page=1'])

    def test_url_with_special_characters(self):
        text = "Complex URL: https://api.example.com/v2/users/~johndoe/profile+settings"
        self.assertEqual(
            FlowUtils.extract_urls_from_text(text),
            ['https://api.example.com/v2/users/~johndoe/profile+settings'])

    def test_no_urls(self):
        text = "This is a text without any URLs."
        self.assertEqual(FlowUtils.extract_urls_from_text(text), [])


class TestAddContextToPrompt(unittest.TestCase):

    def setUp(self):

        def patched_nested_get(nested_key, **kwargs):
            """ Mock implementation of flow_utils.ConfigStore.nested_get """

            mocked_config = {
            'atlassian': {
                'api_token' : 'test_api_token',
                'email' : 'test@email.com',
                'jira_url': 'https://example.atlassian.net',
                'jira_api_endpoint' : "/test/jira/endpoint",
                'jira_project_list': 'PROJ1,PROJ2,PROJ3'
                }
            }
            return FlowUtils.nested_get(mocked_config, nested_key)

        # Create the patcher and start
        self.secrets_patcher = patch('flow_utils.ConfigStore.nested_get', patched_nested_get)
        self.mock_secrets = self.secrets_patcher.start()

    def tearDown(self):
        self.secrets_patcher.stop()

    def test_no_urls_or_jira_issues(self):
        prompt = "This is a simple prompt with no URLs or Jira issues."
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertEqual(result, prompt)

    @patch('utils.flow_utils.TxtGetter')
    def test_with_url(self, mock_txt_getter):
        mock_txt_getter.from_url.return_value = "Mocked URL content"
        prompt = "Check this link: https://example.com"
        exp = prompt + "\n\nContent scraped from web url https://example.com:\nMocked URL content"
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertEqual(result, exp)
        mock_txt_getter.from_url.assert_called_once_with("https://example.com")

    @patch('utils.flow_utils.TxtGetter')
    def test_with_confluence_url(self, mock_txt_getter):
        mock_txt_getter.from_confluence_page.return_value = "Mocked Confluence content"
        prompt = "Check this Confluence page: https://example.atlassian.net/wiki/spaces/TEST"
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertIn("Mocked Confluence content", result)
        called_with = "https://example.atlassian.net/wiki/spaces/TEST"
        mock_txt_getter.from_confluence_page.assert_called_once_with(called_with)

    @patch('utils.flow_utils.TxtGetter')
    def test_with_jira_issue(self, mock_txt_getter):
        mock_txt_getter.from_jira_issues.return_value = "Mocked Jira content"
        prompt = "Check this Jira issue: PROJ1-1234"
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertIn("Mocked Jira content", result)
        mock_txt_getter.from_jira_issues.assert_called_once_with("PROJ1-1234")

    @patch('utils.flow_utils.TxtGetter')
    def test_with_jira_issue_and_trailing_char(self, mock_txt_getter):
        mock_txt_getter.from_jira_issues.return_value = "Mocked Jira content"
        prompt = "Check this Jira issue with a bracket on the end : PROJ1-1234: "
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertIn("Mocked Jira content", result)
        mock_txt_getter.from_jira_issues.assert_called_once_with("PROJ1-1234")

    @patch('utils.flow_utils.TxtGetter')
    def test_with_jira_url(self, mock_txt_getter):
        mock_txt_getter.from_jira_issues.return_value = "Mocked Jira content"
        prompt = "Check this Jira issue: https://example.atlassian.net/browse/PROJ2-5678"
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertIn("Mocked Jira content", result)
        mock_txt_getter.from_jira_issues.assert_called_once_with("PROJ2-5678")

    @patch('utils.flow_utils.TxtGetter')
    def test_with_jira_url_trailingchar(self, mock_txt_getter):
        mock_txt_getter.from_jira_issues.return_value = "Mocked Jira content"
        prompt = "Check this Jira issue: https://example.atlassian.net/browse/PROJ2-5678:"
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertIn("Mocked Jira content", result)
        mock_txt_getter.from_jira_issues.assert_called_once_with("PROJ2-5678")

    @patch('utils.flow_utils.TxtGetter')
    def test_with_multiple_urls_and_issues(self, mock_txt_getter):
        mock_txt_getter.from_url.return_value = "Mocked URL content"
        mock_txt_getter.from_confluence_page.return_value = "Mocked Confluence content"
        mock_txt_getter.from_jira_issues.return_value = "Mocked Jira content"
        prompt = "Check these: https://example.com PROJ1-1234" \
            + " https://example.atlassian.net/wiki/spaces/TEST PROJ3-5678"
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertIn("Mocked Jira content", result)
        mock_txt_getter.from_url.assert_called_once_with("https://example.com")
        mock_txt_getter.from_confluence_page.assert_called_once_with(
            "https://example.atlassian.net/wiki/spaces/TEST")
        mock_txt_getter.from_jira_issues.assert_called_once_with("PROJ1-1234 PROJ3-5678")

class TestFlowUtils(unittest.TestCase):

    def test_format_prompt(self):
        # Test case 1: Basic replacement
        format_str = "Hello, {name}!"
        token_map = {"name": "person.name"}
        value_dict = {"person": {"name": "Alice"}}
        result = FlowUtils.format_prompt(format_str, token_map, value_dict)
        self.assertEqual(result, "Hello, Alice!")

        # Test case 1a: Basic replacement - replace full string
        format_str = "{name}"
        token_map = {"name": "person.name"}
        value_dict = {"person": {"name": "Alice"}}
        result = FlowUtils.format_prompt(format_str, token_map, value_dict)
        self.assertEqual(result, "Alice")

        # Test case 1b: Basic replacement - missing token
        with self.assertRaises(Exception):
            format_str = "{unrecognised}"
            token_map = {"name": "person.name"}
            value_dict = {"person": {"name": "Alice"}}
            result = FlowUtils.format_prompt(format_str, token_map, value_dict)

        # Test case 1b.a: Basic replacement - missing token
        with self.assertRaises(Exception):
            format_str = "hello{un.recognised}goodbye"
            token_map = {"name": "person.name"}
            value_dict = {"person": {"name": "Alice"}}
            result = FlowUtils.format_prompt(format_str, token_map, value_dict)

        # Test case 1c: Replacement value has curly brackets
        format_str = "{name}"
        token_map = {"name": "person.name"}
        value_dict = {"person": {"name": "Alice {in} wonderland"}}
        result = FlowUtils.format_prompt(format_str, token_map, value_dict)
        self.assertEqual(result, "Alice {{in}} wonderland")

        # Test case 2: Multiple replacements
        format_str = "{greeting}, {name}! It's {time}."
        token_map = {
            "greeting": "message.greeting",
            "name": "person.name",
            "time": "current.time"
        }
        value_dict = {
            "message": {"greeting": "Good morning"},
            "person": {"name": "Bob"},
            "current": {"time": "9:00 AM"}
        }
        result = FlowUtils.format_prompt(format_str, token_map, value_dict)
        self.assertEqual(result, "Good morning, Bob! It's 9:00 AM.")

        # Test case 3: Escaping curly brackets in replacement values
        format_str = "The event is in {month}."
        token_map = {"month": "event.month"}
        value_dict = {"event": {"month": "June {summer}"}}
        result = FlowUtils.format_prompt(format_str, token_map, value_dict)
        self.assertEqual(result, "The event is in June {{summer}}.")

        # Test case 4: Mixed scenario with escaping and multiple replacements
        format_str = "{person} is {action} in {place}."
        token_map = {
            "person": "subject.name",
            "action": "verb",
            "place": "location.name"
        }
        value_dict = {
            "subject": {"name": "Charlie"},
            "verb": "swimming",
            "location": {"name": "the {blue} pool"}
        }
        result = FlowUtils.format_prompt(format_str, token_map, value_dict)
        self.assertEqual(result, "Charlie is swimming in the {{blue}} pool.")

        # Test case 5: No replacement needed
        format_str = "This is a plain string."
        result = FlowUtils.format_prompt(format_str, {}, {})
        self.assertEqual(result, "This is a plain string.")

        # Test case 6: Missing value (should raise an exception)
        format_str = "{missing} value"
        token_map = {"missing": ["non_existent"]}
        value_dict = {}
        with self.assertRaises(Exception):
            FlowUtils.format_prompt(format_str, token_map, value_dict)


if __name__ == '__main__':

    unittest.main()
