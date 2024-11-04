import test_helper
test_helper.setup_path()
import unittest
from unittest.mock import patch, MagicMock
from flow_utils import FlowUtils

class TestAddContextToPrompt(unittest.TestCase):

    def setUp(self):
        self.secrets_patcher = patch('flow_utils.st.secrets', new={
            'atlassian': {
                'jira_project_list': 'PROJ1,PROJ2,PROJ3',
                'jira_url': 'https://example.atlassian.net'
            }
        })
        self.mock_secrets = self.secrets_patcher.start()

    def tearDown(self):
        self.secrets_patcher.stop()

    @patch('flow_utils.TxtGetter')
    def test_no_urls_or_jira_issues(self, mock_txt_getter):
        prompt = "This is a simple prompt with no URLs or Jira issues."
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertEqual(result, prompt)

    @patch('flow_utils.TxtGetter')
    def test_with_url(self, mock_txt_getter):
        mock_txt_getter.from_url.return_value = "Mocked URL content"
        prompt = "Check this link: https://example.com"
        expected = prompt + "\n\nContent from https://example.com:\nMocked URL content"
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertEqual(result, expected)
        mock_txt_getter.from_url.assert_called_once_with("https://example.com")

    @patch('flow_utils.TxtGetter')
    def test_with_confluence_url(self, mock_txt_getter):
        mock_txt_getter.from_confluence_page.return_value = "Mocked Confluence content"
        prompt = "Check this Confluence page: https://example.atlassian.net/wiki/spaces/TEST"
        expected = prompt + "\n\nContent from https://example.atlassian.net/wiki/spaces/TEST:\nMocked Confluence content"
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertEqual(result, expected)
        mock_txt_getter.from_confluence_page.assert_called_once_with("https://example.atlassian.net/wiki/spaces/TEST")

    @patch('flow_utils.TxtGetter')
    def test_with_jira_issue(self, mock_txt_getter):
        mock_txt_getter.from_jira_issues.return_value = "Mocked Jira content"
        prompt = "Check this Jira issue: PROJ1-1234"
        expected = prompt + "\n\nMocked Jira content"
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertEqual(result, expected)
        mock_txt_getter.from_jira_issues.assert_called_once_with("PROJ1-1234")

    @patch('flow_utils.TxtGetter')
    def test_with_jira_url(self, mock_txt_getter):
        mock_txt_getter.from_jira_issues.return_value = "Mocked Jira content"
        prompt = "Check this Jira issue: https://example.atlassian.net/browse/PROJ2-5678"
        expected = prompt + "\n\nMocked Jira content"
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertEqual(result, expected)
        mock_txt_getter.from_jira_issues.assert_called_once_with("PROJ2-5678")

    @patch('flow_utils.TxtGetter')
    def test_with_multiple_urls_and_issues(self, mock_txt_getter):
        mock_txt_getter.from_url.return_value = "Mocked URL content"
        mock_txt_getter.from_confluence_page.return_value = "Mocked Confluence content"
        mock_txt_getter.from_jira_issues.return_value = "Mocked Jira content"
        prompt = "Check these: https://example.com PROJ1-1234 https://example.atlassian.net/wiki/spaces/TEST PROJ3-5678"
        expected = (prompt + 
                    "\n\nContent from https://example.com:\nMocked URL content" +
                    "\n\nContent from https://example.atlassian.net/wiki/spaces/TEST:\nMocked Confluence content" +
                    "\n\nMocked Jira content")
        result = FlowUtils.add_context_to_prompt(prompt)
        self.assertEqual(result, expected)
        mock_txt_getter.from_url.assert_called_once_with("https://example.com")
        mock_txt_getter.from_confluence_page.assert_called_once_with("https://example.atlassian.net/wiki/spaces/TEST")
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