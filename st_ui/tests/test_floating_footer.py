# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from unittest.mock import patch, MagicMock
from st_ui.floating_footer import FloatingFooter, example_usage

class TestFloatingFooter(unittest.TestCase):
    @patch("st_ui.floating_footer.st")  # Mock the streamlit module
    def test_example_usage(self, mock_st):
        """
        Test the example_usage function with a mocked Streamlit.
        """

        # Setup mock for st.markdown and st.write
        mock_st.markdown = MagicMock()
        mock_st.write = MagicMock()

        # Call the example_usage function
        example_usage()

        # Check that st.markdown is called for CSS injection
        mock_st.markdown.assert_any_call(
            FloatingFooter.CSS_TEMPLATE.format(
                text_color="gray", font_size="20px"
            ),
            unsafe_allow_html=True,
        )

        # Check that st.markdown is called for HTML injection
        mock_st.markdown.assert_any_call(
            FloatingFooter.HTML_TEMPLATE.format(
                message="Informative text to display"
            ),
            unsafe_allow_html=True,
        )

        # Check that st.markdown is called for adding spacing
        mock_st.markdown.assert_any_call(FloatingFooter.BODY_DIV, unsafe_allow_html=True)

        # Verify st.write calls for main content
        mock_st.write.assert_any_call("This is the main content of the app.")
        mock_st.write.assert_any_call("Add your Streamlit components here.")

if __name__ == "__main__":
    unittest.main()