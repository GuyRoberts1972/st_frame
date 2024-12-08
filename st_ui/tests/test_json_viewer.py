# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch, MagicMock
import json
from st_ui.json_viewer import example_usage, JSONViewer

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

    @patch("streamlit.session_state")
    @patch("streamlit.button")
    @patch("streamlit.rerun")
    @patch("streamlit.write")
    @patch("streamlit.json")
    def test_run_with_json_data(self, mock_json, mock_write, mock_rerun, mock_button, mock_session_state):
        # Mock data
        mock_json_data = {"key": "value"}
        mock_session_state.get.return_value = mock_json_data
        mock_button.side_effect = [False, True]  # Simulate "Done" button clicked on second call

        # Mock class and method
        viewer = JSONViewer()
        viewer.state_key = "test_key"
        viewer.add_download_button = MagicMock()

        # First run, no "Done" button click
        result = viewer.run()
        self.assertTrue(result)
        mock_session_state.get.assert_called_once_with(viewer.state_key)
        mock_write.assert_called_once()
        viewer.add_download_button.assert_called_once_with(mock_json_data)
        mock_json.assert_called_once_with(mock_json_data)

        # Second run, "Done" button clicked
        mock_button.reset_mock()  # Reset to test "Done" functionality
        mock_button.side_effect = [True]  # Simulate "Done" button click
        result = viewer.run()
        self.assertTrue(result)
        mock_session_state.__delitem__.assert_called_once_with(viewer.state_key)
        mock_rerun.assert_called_once()

    @patch("streamlit.session_state")
    def test_run_without_json_data(self, mock_session_state):
        # No JSON data in session state
        mock_session_state.get.return_value = None

        # Mock class and method
        viewer = JSONViewer()
        viewer.state_key = "test_key"

        result = viewer.run()
        self.assertFalse(result)
        mock_session_state.get.assert_called_once_with(viewer.state_key)

if __name__ == "__main__":
    unittest.main()
