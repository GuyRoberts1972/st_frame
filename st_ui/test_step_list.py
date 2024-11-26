# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch, MagicMock
from st_ui.step_list import StepContainer, example_usage

class TestStepContainer(unittest.TestCase):
    def setUp(self):
        self.step_container = StepContainer()

    @patch("st_ui.step_list.st")  # Mock Streamlit
    def test_add_style_called_once(self, mock_st):
        # Ensure _add_style adds style once
        self.step_container._add_style()
        self.step_container._add_style()
        mock_st.markdown.assert_called_once_with(
            StepContainer.style,
            unsafe_allow_html=True
        )
        self.assertTrue(self.step_container.style_added)

    @patch("st_ui.step_list.st")
    def test_render_step_hidden(self, mock_st):
        # Mock the placeholder and container
        mock_placeholder = MagicMock()
        mock_container = MagicMock()
        mock_st.empty.return_value = mock_placeholder
        mock_placeholder.container.return_value = mock_container

        # Test render_step when hidden
        self.step_container.render_step("Step 1", lambda: [], expand=False, hide=True)
        mock_st.empty.assert_called_once()
        mock_placeholder.container.assert_called_once()

    @patch("st_ui.step_list.st")
    def test_render_step_not_hidden(self, mock_st):
        # Mock the expander
        mock_expander = MagicMock()
        mock_st.expander.return_value = mock_expander

        # Test render_step when not hidden
        self.step_container.render_step("Step 1", lambda: [], expand=True, hide=False)
        mock_st.expander.assert_called_once_with("Step 1", True)

    @patch("st_ui.step_list.StepContainer")
    @patch("st_ui.step_list.st")
    def test_example_usage(self, mock_st, mock_step_container):
        # Mock the StepContainer instance
        mock_container = mock_step_container.return_value

        # Call the function
        example_usage()

        # Verify Streamlit title was set
        mock_st.title.assert_called_once_with("Multi-Step Form")

        # Verify render_step was called for each step
        steps = ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"]
        self.assertEqual(mock_container.render_step.call_count, len(steps))
        for i, call in enumerate(mock_container.render_step.call_args_list):
            args, _kwargs = call
            self.assertEqual(args[0], steps[i])  # Check step heading
            self.assertIsNotNone(args[1])  # Content callback is defined

if __name__ == "__main__":
    unittest.main()
