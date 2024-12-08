# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch
import json
from st_ui.json_viewer import example_usage

class TestJSONViewer(unittest.TestCase):
    def test_example_usage(self):

        # Call the example_usage function with no json loaded
        example_usage()

    @patch("streamlit.text_area")
    @patch("streamlit.button")
    @patch("streamlit.error")
    @patch("streamlit.title")
    @patch("st_ui.json_viewer.JSONViewer.view_json")
    def test_example_usage_button_click(self,
                                        mock_view_json,
                                        mock_title,
                                        mock_error,
                                        mock_button,
                                        mock_text_area):
        # Sample default data
        default_data = {
            "name": "John Doe",
            "age": 30,
            "city": "New York",
            "hobbies": ["reading", "swimming", "cycling"]
        }
        default_json = json.dumps(default_data, indent=2)

        # Set up the mocked return values
        mock_text_area.return_value = default_json
        mock_button.return_value = True  # Simulate button click

        # Call the function
        example_usage()

        # Assertions
        mock_title.assert_called_once_with("Example Viewer")
        mock_text_area.assert_called_once_with(
            "Enter your JSON data here:",
            value=default_json,
            height=300
            )
        mock_button.assert_called_once_with("View JSON")
        mock_view_json.assert_called_once_with(default_data)
        mock_error.assert_not_called()

    @patch("streamlit.text_area")
    @patch("streamlit.button")
    @patch("streamlit.error")
    @patch("streamlit.title")
    def test_example_usage_invalid_json(self, mock_title, mock_error, mock_button, mock_text_area):
        # Invalid JSON input
        invalid_json = "{name: John Doe, age: 30, city: New York"  # Missing closing brace

        # Set up the mocked return values
        mock_text_area.return_value = invalid_json
        mock_button.return_value = True  # Simulate button click

        # Call the function
        example_usage()

        # Assertions
        mock_title.assert_called_once_with("Example Viewer")
        mock_text_area.assert_called_once_with(
            "Enter your JSON data here:",
            value=json.dumps({
                "name": "John Doe",
                "age": 30,
                "city": "New York",
                "hobbies": ["reading", "swimming", "cycling"]
            }, indent=2),
            height=300
        )
        mock_button.assert_called_once_with("View JSON")
        mock_error.assert_called_once_with("Invalid JSON format. Please check your input.")


if __name__ == "__main__":
    unittest.main()
