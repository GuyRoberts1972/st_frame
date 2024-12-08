""" Floating footer text for streamlit """
import streamlit as st

class FloatingFooter:
    """Reusable class to show text in a floating footer at the bottom of the page"""

    CSS_TEMPLATE = """
    <style>
    .banner {{
        color: {text_color};
        padding: 10px;
        text-align: right;
        font-size: {font_size};
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        z-index: 1000;
    }}
    </style>
    """

    HTML_TEMPLATE = """
    <div class="banner">
        {message}
    </div>
    """

    BODY_DIV = '<div class="body">'

    @staticmethod
    def show(message: str, text_color: str = "gray", font_size: str = "15px"):
        """ Displays a fixed footer at the bottom of the Streamlit app. """

        # Custom CSS for the banner
        banner_css = FloatingFooter.CSS_TEMPLATE.format(
            text_color=text_color, font_size=font_size
        )

        # HTML for the banner
        banner_html = FloatingFooter.HTML_TEMPLATE.format(message=message)

        # Inject the CSS and HTML
        st.markdown(banner_css, unsafe_allow_html=True)
        st.markdown(banner_html, unsafe_allow_html=True)

        # Add spacing to avoid content overlapping
        st.markdown(FloatingFooter.BODY_DIV, unsafe_allow_html=True)

def example_usage():
    """ Usage illustration """
    FloatingFooter.show("Informative text to display", font_size="20px")
    st.write("This is the main content of the app.")
    st.write("Add your Streamlit components here.")

# Usage Example
if __name__ == "__main__":
    example_usage()
