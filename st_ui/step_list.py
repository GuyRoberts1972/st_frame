""" Displays the steps in a flow """
import streamlit as st

class StepContainer:
    """ The main widget container within which the steps are displayed """

    style = """
            <style>
            /* Font for the expander summary */
            .stExpander details > summary > span > div > p {
                font-size: 25px;
                font-weight: 550;
                }
             .stExpander button > div > p {
                    white-space: nowrap;
                }

            </style>
            """

    def __init__(self):
        self.style_added = False

    def _add_style(self):
        """ add the CSS styling once """
        if self.style_added:
            return

        # Add the style
        st.markdown(StepContainer.style, unsafe_allow_html=True)

        # Flag added
        self.style_added = True

    def render_step(self, step_heading, content_callback, expand, hide):
        """ Display the container and callback for the content """

        # Add the style
        self._add_style()

        # Use a placeholder if we are hidden
        placeholder = None
        if hide:
            placeholder = st.empty()
            container = placeholder.container()
        else:
            container = st.expander(step_heading, expand)

        # Create the content in the container
        with container:

            # Render the body of the step
            buttons = content_callback()

            # Render the buttons
            button_count = len(buttons)
            if button_count > 0:
                spec = [10] * (button_count -1) + [100]
                columns = st.columns(spec=spec)
                col_index = 0
                for button in buttons:
                    with columns[col_index]:
                        st.button(button['text'], key=button['key'], help=button.get('help_text'), on_click=button.get('on_click'))
                    col_index = col_index + 1

        # Empty the place holder if hidden
        if hide:
            placeholder.empty()

def example_usage():
    """ Example of how the class can be used """

    # Define the steps
    steps = ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"]

    # Main content
    st.title("Multi-Step Form")

    def render_step_content(step):
        st.text_input("Enter some text", key=f"edit_{step}")
        st.selectbox("Choose an option", ["Option 1", "Option 2", "Option 3"], key=f"select_{step}")
        buttons =  [
            {
            "text" : "Noop",
            "key"   : f"Noop_{step}"
            },
            {
            "text" : "Toast",
            "key"   : f"toast_{step}",
            "on_click" : lambda: st.toast('Toast')
            },
            {
            "text" : "Balloons",
            "key"   : f"balloons_{step}",
            "on_click" : st.balloons
            },
            {
            "text" : "Snow",
            "key"   : f"snow_{step}",
            "on_click" : st.snow
            }
        ]
        return buttons

    # Display all steps
    step_container = StepContainer()
    flip_flop = False
    for step in steps:

        step_heading = step
        expand = flip_flop
        step_container.render_step(step_heading, lambda step=step: render_step_content(step), expand, False)
        flip_flop  = not flip_flop

if __name__ == '__main__':

    # run the sample
    example_usage()
