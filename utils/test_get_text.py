# pylint: disable=C0116
import unittest
from get_text import TxtGetter, TxtGetterHelpers

class TestTxtGetterHelpers(unittest.TestCase):

    def test_get_nested_values(self):
        data = {"a": 1}
        self.assertEqual(TxtGetterHelpers.get_nested_value(data, "a"), 1)

        data = {"a": {"b": {"c": 3}}}
        self.assertEqual(TxtGetterHelpers.get_nested_value(data, "a.b.c"), 3)

        data = {"a": 1}
        self.assertEqual(TxtGetterHelpers.get_nested_value(data, "b"), "N/A")

        data = {"a": {"b": 2}}
        self.assertEqual(TxtGetterHelpers.get_nested_value(data, "a.c"), "N/A")

        data = {"a": None}
        self.assertEqual(TxtGetterHelpers.get_nested_value(data, "a"), "N/A")

        data = {"a": {"b": None}}
        self.assertEqual(TxtGetterHelpers.get_nested_value(data, "a.b.c"), "N/A")

        data = {"a": 1}
        self.assertEqual(TxtGetterHelpers.get_nested_value(data, "b", default="Not Found"), "Not Found")

        data = {"a": 1}
        self.assertEqual(TxtGetterHelpers.get_nested_value(data, ""), "N/A")

        data = "not a dict"
        self.assertEqual(TxtGetterHelpers.get_nested_value(data, "a"), "N/A")

    def test_split_string(self):
        # Test cases
        test_cases = [
            ("a b,c,,,,,d", ["a", "b", "c", "d"]),
            ("apple banana,cherry", ["apple", "banana", "cherry"]),
            ("  red  green   blue  ", ["red", "green", "blue"]),
            ("one,two,  three   four,five", ["one", "two", "three", "four", "five"]),
            ("single", ["single"]),
            ("  ", []),  # Empty string after stripping
            (",,  ,,", [])  # Only delimiters
        ]

        for input_string, expected_output in test_cases:
            with self.subTest(input_string=input_string):
                actual_output = TxtGetterHelpers.split_string(input_string)
                self.assertEqual(actual_output, expected_output)

if __name__ == '__main__':
    unittest.main()