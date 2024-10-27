import unittest
import test_helper
test_helper.setup_path()
from flow_utils import FlowUtils
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