# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch, MagicMock
import streamlit as st
from st_ui.option_selector import OptionSelector, example_usage

class TestOptionSelector(unittest.TestCase):

    def setUp(self):
        self.options = {
            "fruits": {
                "icon": "\U0001F34E",  # Red Apple
                "title": "Fruits",
                "description": "Fresh and juicy fruits"
            },
            "vegetables": {
                "icon": "\U0001F955",  # Carrot
                "title": "Vegetables",
                "description": "Healthy and nutritious veggies"
            },
        }
        self.get_sub_options = lambda x: {
            "sub1": {"title": "Sub1", "description": "Description 1", "enabled": True},
            "sub2": {"title": "Sub2", "description": "Description 2", "enabled": True},
            "sub3": {"title": "Sub3", "description": "Description 3", "enabled": False}
        }
        self.on_select = MagicMock()
        self.on_cancel = MagicMock()
        self.selector = OptionSelector(
            self.options,
            self.get_sub_options,
            self.on_select,
            self.on_cancel)

    @patch('streamlit.button')
    @patch('streamlit.columns')
    def test_render_main_options(self, mock_columns, mock_button):
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_button.return_value = False
        self.selector._render_main_options()
        self.assertEqual(mock_button.call_count, 2)

    @patch('streamlit.radio')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    def test_render_sub_options(self, mock_columns, mock_button, mock_radio):
        st.session_state.op_sel_selected_option = self.options["fruits"]
        st.session_state.op_sel_selected_option_key = "fruits"
        mock_columns.return_value = [MagicMock(), MagicMock()]
        mock_button.return_value = False
        mock_radio.return_value = 0  # Select the first sub-option
        self.selector._render_sub_options()
        mock_radio.assert_called_once()
        self.assertEqual(mock_button.call_count, 2)

    @patch('streamlit.radio')
    @patch('streamlit.button')
    def test_disabled_sub_option(self, mock_button, mock_radio):
        st.session_state.op_sel_selected_option = self.options["fruits"]
        st.session_state.op_sel_selected_option_key = "fruits"
        mock_radio.return_value = 2  # Select the third (disabled) sub-option
        mock_button.side_effect = [False, False]  # Neither button pressed
        self.selector._render_sub_options()
        mock_button.assert_any_call(self.selector.STRINGS["ACTION_CONFIRM_BUTTON"], disabled=True)

    @patch('streamlit.radio')
    @patch('streamlit.button')
    def test_on_select_callback(self, mock_button, mock_radio):
        st.session_state.op_sel_selected_option = self.options["fruits"]
        st.session_state.op_sel_selected_option_key = "fruits"
        mock_radio.return_value = 0  # Select the first (enabled) sub-option
        mock_button.side_effect = [True, False]  # Confirm button pressed
        self.selector._render_sub_options()
        self.on_select.assert_called_once_with(
            "fruits",
            "sub1",
            {"title": "Sub1", "description": "Description 1", "enabled": True}
        )

    @patch('streamlit.radio')
    @patch('streamlit.button')
    def test_on_cancel_callback(self, mock_button, mock_radio):
        st.session_state.op_sel_selected_option = self.options["fruits"]
        st.session_state.op_sel_selected_option_key = "fruits"
        mock_radio.return_value = 0  # Select any sub-option
        mock_button.side_effect = [False, True]  # Back button pressed
        self.selector._render_sub_options()
        self.on_cancel.assert_called_once()

    @patch("st_ui.option_selector.st")  # Mock the streamlit module
    def test_example_usage(self, mock_st):

        # Setup mock for st.markdown and st.write
        mock_st.markdown = MagicMock()
        mock_st.write = MagicMock()

        # Call the example_usage function
        example_usage()


if __name__ == "__main__":
    unittest.main()
