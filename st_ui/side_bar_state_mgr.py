"""  A sidebar navigator that manages sessions state switches """
import json
import os
import tempfile
import streamlit as st
from streamlit_option_menu import option_menu
from utils.storage_utils import StorageBackend
from st_ui.json_viewer import JSONViewer
from st_ui.auth import AuthBase


class SideBarStateMgr:
    """ Main class to render side nav bar and manage state switches """

    # Class-level string table
    STRINGS = {
        'USER_LOGOUT': "Logout",
        'CREATE_NEW_STATE': "New Session",
        'ACTIONS_HEADING' : 'Session Actions',
        'STATE_NAV_HEADING' : 'Session History',
        'NEW_STATE_BASENAME' : 'Session_{0}',
        'SAVED_STATES': "Saved:",
        'ACTION_CONFIRM': "Ok",
        'ACTION_CANCEL': "Cancel",
        'STATE_CREATED': "'{0}' created.",
        'STATE_DUPLICATED_CREATED': "'{0}' created.",
        'STATE_RENAME_OK': "'{0}' renamed.",
        'STATE_RENAME_DUPLICATE': "'{0}' already exists.",
        'STATE_RENAME_ERROR': "'{0}' renamed failed",
        'STATE_DELETED': "'{0}' deleted.",
        'STATE_LOADED': "'{0}' loaded.",
        'DEFAULT_STATE': 'default'
    }

    def __init__(self, key_storage_map, saved_states_dir):

        # Store
        self.key_storage_map = key_storage_map

        # Get the storage class from factory
        self.storage = StorageBackend.get_storage(saved_states_dir)

        # Handle state loading at the beginning of the script
        if 'sbsm_state_to_load' in st.session_state:
            self.load_session_from_state(st.session_state.sbsm_state_to_load)
            del st.session_state.sbsm_state_to_load

        if 'sbsm_current_state' not in st.session_state:
            st.session_state.sbsm_current_state = None

        if 'sbsm_renaming_state' not in st.session_state:
            st.session_state.sbsm_renaming_state = None

        # Setup the side bar
        self.setup_sidebar()

    @staticmethod
    def key_matches_patterns(key, patterns):
        """ Return true if the key matches the regex patterns """
        for pattern in patterns:
            if pattern.endswith('*'):
                if key.startswith(pattern[:-1]):
                    return True
            elif key == pattern:
                return True
        return False

    @staticmethod
    def key_is_persistant(key, key_storage_map):
        """ persistant keys get saved and cleared and loaded with state changes """
        return SideBarStateMgr.key_matches_patterns(key, key_storage_map['persistant'])

    @staticmethod
    def key_is_volatile(key, key_storage_map):
        """ volatile keys get cleared with state changes"""
        volatile = SideBarStateMgr.key_matches_patterns(key, key_storage_map['volatile'])
        return volatile

    @staticmethod
    def set_session_state(key_storage_map, loaded_state):
        """ Set the state data on the loaded state
        Note: Clears any peristable keys by setting to None
        """

        # Clear any that are persistant or volatile first
        keys = list(st.session_state.keys())
        for key in keys:
            # Important: Set to None to clear. Deleting key does not clear widget cache
            if SideBarStateMgr.key_is_persistant(key, key_storage_map):
                st.session_state[key] = None
            elif SideBarStateMgr.key_is_volatile(key, key_storage_map):
                st.session_state[key] = None

        # Now set
        st.session_state.update(loaded_state)

    def get_state_relative_path(self, name):
        """ Get the relative path and file name to store the state in """
        rel_path = f"{name}.json"
        return rel_path

    def save_state(self, name, key_storage_map):
        """ Save the named state to storage """
        state_to_save = {key: st.session_state[key] for key in st.session_state
                         if SideBarStateMgr.key_is_persistant(key, key_storage_map)}
        rel_path = self.get_state_relative_path(name)
        self.storage.write_text(rel_path, json.dumps(state_to_save))


    def load_state(self, name, key_storage_map):
        """ Load the state for the name """
        rel_path = self.get_state_relative_path(name)
        loaded_state = self.storage.read_text(rel_path)
        loaded_state = json.loads(loaded_state)
        return {key: loaded_state[key] for key in loaded_state
                if SideBarStateMgr.key_is_persistant(key, key_storage_map)}

    def get_saved_states(self):
        """ Get a list of all the stored states """
        dir_list = self.storage.list_files('')
        return [os.path.splitext(f)[0] for f in dir_list if f.endswith('.json')]

    def delete_state(self, name):
        """ Remove the state with the specified name """
        rel_path = self.get_state_relative_path(name)
        self.storage.delete(rel_path)

    def rename_state(self, old_name, new_name):
        """ Rename the state in storage """
        old_rel_path = self.get_state_relative_path(old_name)
        new_rel_path = self.get_state_relative_path(new_name)
        self.storage.rename(old_rel_path, new_rel_path)

    def duplicate_state(self, name):
        """ Make a copy of name, check for clashes and increment an index, return new name """
        index = 1
        while True:
            new_name = f'{name}_{index}'
            source_rel_path = self.get_state_relative_path(name)
            destination_rel_path = self.get_state_relative_path(new_name)

            if not self.storage.file_exists(destination_rel_path):
                try:
                    self.storage.copy(source_rel_path, destination_rel_path)
                    return new_name
                except IOError as exc:
                    raise RuntimeError(f"Error copying file: {exc}") from exc

            index += 1

    @staticmethod
    def set_status_message(message, message_type='info'):
        """ Show an informational status message """
        st.session_state.sbsm_status_message = message
        st.session_state.sbsm_status_type = message_type

    @staticmethod
    def show_status_message():
        """ Show a status message """
        if None is not st.session_state.get('sbsm_status_type'):
            if st.session_state.sbsm_status_type == 'success':
                st.sidebar.success(st.session_state.sbsm_status_message)
            elif st.session_state.sbsm_status_type == 'error':
                st.sidebar.error(st.session_state.sbsm_status_message)
            elif st.session_state.sbsm_status_type == 'info':
                st.sidebar.info(st.session_state.sbsm_status_message)
            del st.session_state.sbsm_status_message
            del st.session_state.sbsm_status_type

    def setup_state_option_menu(self, saved_states, on_state_select):
        """ Render the state options menu and manage selected state

            setup the menu and the on_state_select call back
            if sbsm_manual_set_state_selected is set on session state then select that in the menu
            if sbsm_current_state is not set, select the first state and load it into session
        """


        # State menu
        if len(saved_states) > 0:

            # Do we need to force a selection 'manually'
            if None is not st.session_state.get('sbsm_manual_set_state_selected'):

                # Get the index - default to 0
                sbsm_manual_set_state_selected = st.session_state.sbsm_manual_set_state_selected
                if sbsm_manual_set_state_selected in saved_states:
                    manual_select = saved_states.index(sbsm_manual_set_state_selected)
                else:
                    manual_select = 0

                # Remove flag
                del st.session_state.sbsm_manual_set_state_selected

            # Is current state not set?
            elif  None is st.session_state.get('sbsm_current_state'):

                # Default to first - Cases: App just loaded or selected item deleted
                manual_select = 0
                self.load_session_from_state(saved_states[0])

            else:
                # No manual select - use the menus state
                manual_select = None

            # Use the primary colour as hover
            hover_color = st.get_option('theme.primaryColor')

            # Create the widget
            state_nav_heading = SideBarStateMgr.STRINGS['STATE_NAV_HEADING']
            state_icons = ["chat-left"] * len(saved_states)
            option_menu(
                menu_title=state_nav_heading,
                menu_icon="chat-left-dots",
                options=saved_states,
                icons=state_icons,
                default_index=0,
                on_change=on_state_select,
                key='sbsm_on_state_select_key',
                styles={ "nav-link": { "--hover-color": hover_color }},
                manual_select=manual_select
            )

    def create_container(self, heading, container_key):
        """ Create a containe for widgets with styling """

        # Custom styling for the container
        container_bkg_col = st.get_option('theme.backgroundColor')

        css_template = f"""
            <style>
            /* The container */
            .st-key-{container_key} {{
                padding: 20px;
                border-radius: .5rem;
                background-color: {container_bkg_col};
            }}

            /* Get rid of text box message */
            .st-key-{container_key} .stTextInput {{
                width: fit-content;
            }}

            /* Grey background for edit input */
            .st-key-{container_key} input {{
                background-color: rgb(240, 242, 246);
            }}

            /* Hide the 'press enter to apply' */
            .st-key-sbsm_rename_state_edit div[data-testid="InputInstructions"] {{
                visibility: hidden;
            }}

            /* Make the  title fit & match */
            .st-key-{container_key} hr {{
                width: 90%;
                background-color: rgb(227 231 241);
            }}
            </style>
        """

        # Inject the CSS with the container_key
        st.markdown(css_template, unsafe_allow_html=True)

        # Create and return
        container = st.container(key=container_key)
        container.subheader(heading, divider='grey')
        return container

    def setup_sidebar(self):
        """ Main function to set the side bar up """

        # Get the saved states
        saved_states = self.get_saved_states()

        def on_state_select(key):
            """ Handle state selection """

            # Get the selected state using the key
            selected_state = st.session_state.get(key, None)
            if selected_state in saved_states:
                if selected_state != st.session_state.get('sbsm_current_state'):
                    st.session_state.sbsm_state_to_load = selected_state

        def do_action_create_new_state():
            """ Create a new state """

            # Make a unique name
            counter = 1
            new_state_name = SideBarStateMgr.STRINGS['NEW_STATE_BASENAME'].format(counter)

            while new_state_name in saved_states:
                counter += 1
                new_state_name = SideBarStateMgr.STRINGS['NEW_STATE_BASENAME'].format(counter)

            # Clean slate and save
            SideBarStateMgr.set_session_state(self.key_storage_map, {})
            self.save_state(new_state_name, self.key_storage_map)

            # Set the current state and flag option menu needs to be set
            st.session_state.sbsm_current_state = new_state_name
            st.session_state.sbsm_manual_set_state_selected = new_state_name

            # Set message
            SideBarStateMgr.set_status_message(
                SideBarStateMgr.STRINGS['STATE_CREATED'].format(new_state_name))

            # Clear action flag
            st.session_state.sbsm_selected_action = None

            # Go again
            st.rerun()

        def do_action_rename():
            """ Rename a state """
            # Prompt for rename
            new_name = st.text_input('Rename:', value=current_state, key="sbsm_rename_state_edit")
            col1, col2 = st.columns(2)

            # Confirm
            if col1.button(
                SideBarStateMgr.STRINGS['ACTION_CONFIRM'],
                key=f"sbsm_confirm_rename_{current_state}"):

                # Rename storage
                if current_state != new_name:

                    # Check for dupes
                    if new_name in saved_states:
                        SideBarStateMgr.set_status_message(
                            SideBarStateMgr.STRINGS['STATE_RENAME_DUPLICATE'].format(new_name),
                            'info')
                    else:
                        try:
                            # Try rename, set curent states and display message
                            self.rename_state(current_state, new_name)
                            st.session_state.sbsm_current_state = new_name
                            st.session_state.sbsm_manual_set_state_selected = new_name
                            SideBarStateMgr.set_status_message(
                                SideBarStateMgr.STRINGS['STATE_RENAME_OK'].format(new_name)
                                )

                        except Exception as e: #pylint: disable=broad-exception-caught
                            # Failed, display the message including the specific error
                            err_msg = SideBarStateMgr.STRINGS['STATE_RENAME_ERROR'].format(new_name)
                            detailed_err_msg = f"{err_msg}\nError details: {str(e)}"
                            SideBarStateMgr.set_status_message(detailed_err_msg, 'error')

                # clear action and rerun
                st.session_state.sbsm_selected_action = None
                st.rerun()

            # Cancel
            if col2.button(
                    SideBarStateMgr.STRINGS['ACTION_CANCEL'],
                    key=f"sbsm_cancel_rename_{current_state}"):
                st.session_state.sbsm_selected_action = None
                st.rerun()

        def do_action_delete():
            """ Delete the selected state """

            st.write(f"Delete'{current_state}'?")
            col1, col2 = st.columns(2)

            # Confirm delete
            if col1.button(
                    SideBarStateMgr.STRINGS['ACTION_CONFIRM'],
                    key=f"sbsm_confirm_delete_{current_state}"):

                # Delete file and clear current state
                self.delete_state(current_state)
                st.session_state.sbsm_current_state = None

                # Set status message, clear action and rerun
                SideBarStateMgr.set_status_message(
                    SideBarStateMgr.STRINGS['STATE_DELETED'].format(current_state)
                    )
                st.session_state.sbsm_selected_action = None
                st.rerun()

            # Cancel delete
            if col2.button(
                    SideBarStateMgr.STRINGS['ACTION_CANCEL'],
                    key=f"sbsm_cancel_delete_{current_state}"):
                st.session_state.sbsm_selected_action = None
                st.rerun()

        def do_action_view_json():
            """ Display the json for the state """
            st.session_state.sbsm_selected_action = None
            JSONViewer.view_json(st.session_state)

        def do_action_duplicate():
            """ Duplicate the selected state """

            # Delete file and clear current state
            dupe_state = self.duplicate_state(current_state)
            st.session_state.sbsm_current_state = dupe_state

            # Set status message, clear action and rerun
            status_msg = SideBarStateMgr.STRINGS['STATE_DUPLICATED_CREATED'].format(dupe_state)
            SideBarStateMgr.set_status_message(status_msg)
            st.session_state.sbsm_selected_action = None
            st.rerun()

        # Render
        with st.sidebar:

            # Container for user
            user_name = AuthBase.get_auth().get_username()
            user_heading = f"User: {user_name}"
            user_container = self.create_container(user_heading, 'customer_user_container')
            with user_container:
                # Logout
                if st.button(SideBarStateMgr.STRINGS['USER_LOGOUT']):
                    AuthBase.clear_auth()
                    st.rerun()

            # Container for actions and related widgets
            actions_heading = SideBarStateMgr.STRINGS['ACTIONS_HEADING']
            action_container = self.create_container(actions_heading, 'custom_action_container')
            with action_container:

                # Our actions
                new_session_action = SideBarStateMgr.STRINGS['CREATE_NEW_STATE']
                actions = [new_session_action, 'Rename', 'Delete', "Duplicate", "View JSON"]

                def on_action_select(selected_action=None):
                    """ Handle action selection by setting the selected action on the key """
                    # Take the selected action from the select if not provided
                    if None is selected_action:
                        selected_action = st.session_state.get('sbsm_action_selector')
                    if selected_action in actions:
                        st.session_state['sbsm_selected_action'] = selected_action

                def render_actions_select(actions):
                    """ Show a drop down. Always set to first item. Callback on select. """
                    st.session_state['sbsm_action_selector'] = None
                    st.selectbox(
                        'Action Selection',
                        options=actions,
                        key='sbsm_action_selector',
                        label_visibility = 'collapsed',
                        index=None,
                        placeholder='More...',
                        on_change=on_action_select
                    )

                # Actions button and selector
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(new_session_action):
                        on_action_select(new_session_action)
                with col2:
                    # Actions select drop down
                    selected_actions = [x for x in actions if x != new_session_action]
                    render_actions_select(selected_actions)

                # Get the current state and check valid
                current_state = st.session_state.get('sbsm_current_state', None)
                if current_state in saved_states:

                    # Get the selected action
                    selected_action = st.session_state.get('sbsm_selected_action', None)

                    # Handle New
                    if selected_action == new_session_action:
                        do_action_create_new_state()

                    # Handle Rename
                    elif  selected_action == "Rename":
                        do_action_rename()

                    # Handle Duplicate
                    elif selected_action == "Duplicate":
                        do_action_duplicate()

                    # Handle Delete
                    elif selected_action == "Delete":
                        do_action_delete()

                    # Handle Delete
                    elif selected_action == "View JSON":
                        do_action_view_json()


            # Render the main nav
            self.setup_state_option_menu(saved_states, on_state_select)

            # Show status message at the bottom of the sidebar
            SideBarStateMgr.show_status_message()

    def save_session_to_state(self):
        """ Save session state using the current state name, use the default state name if none """
        # Default current state if not set
        if not st.session_state.sbsm_current_state:
            st.session_state.sbsm_current_state = SideBarStateMgr.STRINGS['DEFAULT_STATE']

        # Save it
        self.save_state(st.session_state.sbsm_current_state, self.key_storage_map)

    def load_session_from_state(self, state_to_load):
        """ (re) load from the state into the current sesson """

        loaded_state = self.load_state(state_to_load, self.key_storage_map)
        SideBarStateMgr.set_session_state(self.key_storage_map, loaded_state)
        st.session_state.sbsm_current_state = state_to_load
        SideBarStateMgr.set_status_message(
            SideBarStateMgr.STRINGS['STATE_LOADED'].format(state_to_load))

    def get_current_state_name(self, default=''):
        """ Get the name of the current state - or return a default """
        return st.session_state.get('sbsm_current_state', default)


def example_usage():
    """Function to illustrate usage."""

    # Set Streamlit page configuration
    st.set_page_config(layout="wide")

    # Setup state manager - specify state keys to persist
    key_storage_map = {"persistant": ['p_*'], "volatile": ['v_*']}

    # Create a temporary directory per session
    key = 'SideBarStateMgr_example'
    temp_dir = st.session_state.get(key)
    if temp_dir is None:
        temp_dir = tempfile.mkdtemp(prefix=f"{key}_")
        st.session_state[key] = temp_dir

    # Initialize the state manager with the temp directory
    state_manager = SideBarStateMgr(key_storage_map, temp_dir)

    st.title("Example App To Demo State Manager")

    # Different storage types
    st.text_input("Persistant Text:", key='p_text')
    st.text_input("Volatile Text:", key='v_text')
    st.text_input("Normal Text:", key='text')

    # Display current state name
    current_state_name = state_manager.get_current_state_name()
    st.write(f"Current State: {current_state_name}")

    # Save it
    state_manager.save_session_to_state()




if __name__ == "__main__":
    example_usage()
