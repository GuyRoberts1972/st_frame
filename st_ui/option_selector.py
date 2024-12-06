""" Streamlit functionality to select an option and sub option """
from typing import Dict, Callable, Any
import streamlit as st

class OptionSelector:
    """
    A reusable class for creating a Streamlit app with selectable options and sub-options.
    """

    # Class-level string table
    STRINGS = {
        "TITLE": "Choose an Option",
        "SUB_OPTION_PROMPT": "Please choose a sub-option:",
        "ACTION_CONFIRM_BUTTON": "Confirm",
        "BACK_BUTTON": "Back",
        "SUCCESS_MESSAGE": "You selected {sub_option} from {main_option}!",
        "DISABLED_OPTION": "{option} (Coming Soon)"
    }

    def __init__(self,
                 options: Dict[str, Dict[str, Any]],
                 get_sub_options: Callable[[str], Dict[str, Dict[str, Any]]],
                 on_select: Callable[[str, str, Dict[str, Any]], None],
                 on_cancel: Callable[[], None]):
        """
        Initialize the OptionSelector.

        :param options: Dictionary of main options, keyed by unique identifiers.
        :param get_sub_options: Function to get sub-options for a main option.
                                Receives the option key and returns a dictionary of sub-options.
        :param on_select: Callback function when an option is selected.
                          Receives main option key, sub-option key, and full sub-option dict.
        :param on_cancel: Callback function when selection is cancelled.
        """
        self.options = options
        self.get_sub_options = get_sub_options
        self.on_select = on_select
        self.on_cancel = on_cancel

        # Initialize session state
        if 'op_sel_selected_option' not in st.session_state:
            st.session_state.op_sel_selected_option = None
        if 'op_sel_selected_option_key' not in st.session_state:
            st.session_state.op_sel_selected_option_key = None

    def clear_state(self):
        """ Clear state - i.e. when done """

        # Initialize session state
        if 'op_sel_selected_option' in st.session_state:
            del st.session_state.op_sel_selected_option
        if 'op_sel_selected_option_key' in st.session_state:
            del st.session_state.op_sel_selected_option_key

    def render(self):
        """Render the Streamlit app."""
        st.title(self.STRINGS["TITLE"])

        if st.session_state.op_sel_selected_option is None:
            self._render_main_options()
        else:
            self._render_sub_options()

    def _render_main_options(self):
        """Render the main options grid."""
        cols = st.columns(2)
        for i, (key, option) in enumerate(self.options.items()):
            with cols[i % 2]:
                button_text = f"{option['icon']} **{option['title']}**\n\n{option['description']}"
                if st.button(button_text,key=f"main_{key}"):
                    st.session_state.op_sel_selected_option = option
                    st.session_state.op_sel_selected_option_key = key
                    st.rerun()


    def _render_sub_options(self):
        """Render the sub-options for the selected main option."""
        st.write(f"You selected: {st.session_state.op_sel_selected_option['title']}")
        st.write(self.STRINGS["SUB_OPTION_PROMPT"])
        sub_options = self.get_sub_options(st.session_state.op_sel_selected_option_key)

        # Create a list of option names, disabling those that are not enabled
        option_keys = list(sub_options.keys())
        option_names = [
            self.STRINGS["DISABLED_OPTION"].format(option=sub_options[key]['title'])
            if not sub_options[key]['enabled'] else sub_options[key]['title']
            for key in option_keys
        ]

        def format_func(i):
            return option_names[i]

        selected_index = st.radio(
            "Sub-options",
            range(len(option_names)),
            format_func=format_func
        )

        selected_key = option_keys[selected_index]
        selected_sub_option = sub_options[selected_key]

        st.write(f"Description: {selected_sub_option['description']}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                self.STRINGS["ACTION_CONFIRM_BUTTON"],
                disabled=not selected_sub_option['enabled']):

                self.on_select(st.session_state.op_sel_selected_option_key, selected_key, selected_sub_option)
                st.success(self.STRINGS["SUCCESS_MESSAGE"].format(
                    sub_option=selected_sub_option['title'],
                    main_option=st.session_state.op_sel_selected_option['title']
                ))

        with col2:
            if st.button(self.STRINGS["BACK_BUTTON"]):
                st.session_state.op_sel_selected_option = None
                st.session_state.op_sel_selected_option_key = None
                self.on_cancel()
                st.rerun()

def example_usage():
    """ Usage illustration """

    options = {
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
        "meats": {
            "icon": "\U0001F356",  # Meat on Bone
            "title": "Meats",
            "description": "Protein-rich meat options"
        },
        "dairy": {
            "icon": "\U0001F9C0",  # Cheese Wedge
            "title": "Dairy",
            "description": "Calcium-rich dairy products"
        },
    }

    def get_sub_options(option_key):
        #pylint: disable=line-too-long
        sub_options = {
            "fruits": {
                "apple": {"title": "Apple", "description": "Red and crunchy", "enabled": True},
                "banana": {"title": "Banana", "description": "Yellow and soft", "enabled": True},
                "orange": {"title": "Orange", "description": "Orange and juicy", "enabled": True},
                "dragon_fruit": {"title": "Dragon Fruit", "description": "Exotic and colorful", "enabled": False}
            },
            "vegetables": {
                "carrot": {"title": "Carrot", "description": "Orange and crunchy", "enabled": True},
                "broccoli": {"title": "Broccoli", "description": "Green, nutritious", "enabled": True},
                "spinach": {"title": "Spinach", "description": "Leafy and iron-rich", "enabled": True},
                "artichoke": {"title": "Artichoke", "description": "Unique and flavorful", "enabled": False}
            },
            "meats": {
                "chicken": {"title": "Chicken", "description": "Lean and versatile", "enabled": True},
                "beef": {"title": "Beef", "description": "Rich and flavorful", "enabled": True},
                "pork": {"title": "Pork", "description": "Tender and juicy", "enabled": True},
                "venison": {"title": "Venison", "description": "Gamey and lean", "enabled": False}
            },
            "dairy": {
                "milk": {"title": "Milk", "description": "Creamy and nutritious", "enabled": True},
                "cheese": {"title": "Cheese", "description": "Variety of flavors", "enabled": True},
                "yogurt": {"title": "Yogurt", "description": "Probiotic-rich", "enabled": True},
                "kefir": {"title": "Kefir", "description": "Fermented and tangy", "enabled": False}
            },
        }
        return sub_options[option_key]

    def on_select(main_option_key, sub_option_key, sub_option_dict):
        main_option = options[main_option_key]  # Get the main option dict using the key
        st.write(f"Selected {sub_option_dict['title']} (key: {sub_option_key}) from {main_option['title']}")
        st.write(f"Main option key: {main_option_key}")
        st.write(f"Main option details: {main_option}")
        st.write(f"Sub-option details: {sub_option_dict}")

    def on_cancel():
        st.write("Selection cancelled")

    selector = OptionSelector(options, get_sub_options, on_select, on_cancel)
    selector.render()

if __name__ == "__main__":
    example_usage()
