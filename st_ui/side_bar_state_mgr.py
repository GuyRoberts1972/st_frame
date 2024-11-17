"""  A sidebar navigator that manage sessions state switches """
import streamlit as st
import json
import os
from streamlit_option_menu import option_menu



class SideBarStateMgr:
    # Class-level string table
    STRINGS = {
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

    # Get saved states
    saved_states_dir = st.secrets['paths']['saved_states']

    @staticmethod
    def key_matches_patterns(key, patterns):
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
        
    @staticmethod
    def get_cur_saved_states_dir():
        return SideBarStateMgr.saved_states_dir
    
    @staticmethod
    def get_state_path(name):
        return os.path.join(SideBarStateMgr.get_cur_saved_states_dir(), f"{name}.json")
    
    @staticmethod
    def save_state(name, key_storage_map):
        if not os.path.exists(SideBarStateMgr.get_cur_saved_states_dir()):
            os.makedirs()
        state_to_save = {key: st.session_state[key] for key in st.session_state 
                         if SideBarStateMgr.key_is_persistant(key, key_storage_map)}
        with open(SideBarStateMgr.get_state_path(name), 'w') as f:
            json.dump(state_to_save, f)

    @staticmethod
    def load_state(name, key_storage_map):
        with open(SideBarStateMgr.get_state_path(name), 'r') as f:
            loaded_state = json.load(f)
        return {key: loaded_state[key] for key in loaded_state 
                if SideBarStateMgr.key_is_persistant(key, key_storage_map)}

    @staticmethod
    def get_saved_states():
        return [os.path.splitext(f)[0] for f in os.listdir(SideBarStateMgr.get_cur_saved_states_dir()) if f.endswith('.json')]

    @staticmethod
    def delete_state(name):
        os.remove(SideBarStateMgr.get_state_path(name))

    @staticmethod
    def rename_state(old_name, new_name):
        os.rename(SideBarStateMgr.get_state_path(old_name), SideBarStateMgr.get_state_path(new_name))

    @staticmethod
    def duplicate_state(name):
        """ Make a copy of name, check for clashes and increment an index, return new name """
        import shutil
        index = 1
        while True:
            new_name = f'{name}_{index}'
            source_path = SideBarStateMgr.get_state_path(name)
            destination_path = SideBarStateMgr.get_state_path(new_name)
            
            if not os.path.exists(destination_path):
                try:
                    shutil.copy2(source_path, destination_path)
                    return new_name
                except IOError as e:
                    raise (f"Error copying file: {e}")
            
            index += 1

    @staticmethod
    def set_status_message(message, message_type='info'):
        st.session_state.sbsm_status_message = message
        st.session_state.sbsm_status_type = message_type

    @staticmethod
    def show_status_message():
        if None != st.session_state.get('sbsm_status_type'):
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
            if sbsm_current_state is not set then select the first state and load that state into session
        """
        

        # State menu
        if len(saved_states) > 0:

            # Do we need to force a selection 'manually'
            if None != st.session_state.get('sbsm_manual_set_state_selected'):

                # Get the index - default to 0
                sbsm_manual_set_state_selected = st.session_state.sbsm_manual_set_state_selected
                if sbsm_manual_set_state_selected in saved_states:
                    manual_select = saved_states.index(sbsm_manual_set_state_selected)
                else: 
                    manual_select = 0
                
                # Remove flag
                del st.session_state.sbsm_manual_set_state_selected

            # Is current state not set?
            elif  None == st.session_state.get('sbsm_current_state'): 
                
                # Default to first - Cases: App just loaded or selected item deleted
                manual_select = 0
                self.load_session_from_state(saved_states[0])
            
            else:
                # No manual select - use the menus state
                manual_select = None
            
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
                styles={ "nav-link": { "--hover-color": "#eee" }},
                manual_select=manual_select
            )

    def setup_sidebar(self):

        # Get the saved states
        saved_states = SideBarStateMgr.get_saved_states()
        
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
            SideBarStateMgr.save_state(new_state_name, self.key_storage_map)

            # Set the current state and flag option menu needs to be set
            st.session_state.sbsm_current_state = new_state_name
            st.session_state.sbsm_manual_set_state_selected = new_state_name
            
            # Set message
            SideBarStateMgr.set_status_message(SideBarStateMgr.STRINGS['STATE_CREATED'].format(new_state_name))

            # Clear action flag
            st.session_state.sbsm_selected_action = None

            # Go again
            st.rerun()

        def do_action_rename():
            """ Rename a state """
            # Prompt for rename
            new_name = st.text_input('Rename:', value=current_state, key=f"sbsm_rename_state_edit")
            col1, col2 = st.columns(2)

            # Confirm
            if col1.button(SideBarStateMgr.STRINGS['ACTION_CONFIRM'], key=f"sbsm_confirm_rename_{current_state}"):
                
                # Rename storage
                if current_state != new_name:

                    # Check for dupes
                    if new_name in saved_states:
                        SideBarStateMgr.set_status_message(SideBarStateMgr.STRINGS['STATE_RENAME_DUPLICATE'].format(new_name), 'info')
                    else: 
                        try: 
                            # Try rename, set curent states and display message
                            SideBarStateMgr.rename_state(current_state, new_name)
                            st.session_state.sbsm_current_state = new_name
                            st.session_state.sbsm_manual_set_state_selected = new_name
                            SideBarStateMgr.set_status_message(SideBarStateMgr.STRINGS['STATE_RENAME_OK'].format(new_name))

                        except:
                            # Failed
                            SideBarStateMgr.set_status_message(SideBarStateMgr.STRINGS['STATE_RENAME_ERROR'].format(new_name), 'error')

                # clear action and rerun
                st.session_state.sbsm_selected_action = None
                st.rerun()

            # Cancel
            if col2.button(SideBarStateMgr.STRINGS['ACTION_CANCEL'], key=f"sbsm_cancel_rename_{current_state}"):
                st.session_state.sbsm_selected_action = None
                st.rerun()

        def do_action_delete():
            """ Delete the selected state """

            st.write(f"Delete'{current_state}'?")
            col1, col2 = st.columns(2)

            # Confirm delete
            if col1.button(SideBarStateMgr.STRINGS['ACTION_CONFIRM'], key=f"sbsm_confirm_delete_{current_state}"):
                
                # Delete file and clear current state
                SideBarStateMgr.delete_state(current_state)
                st.session_state.sbsm_current_state = None
                
                # Set status message, clear action and rerun
                SideBarStateMgr.set_status_message(SideBarStateMgr.STRINGS['STATE_DELETED'].format(current_state))
                st.session_state.sbsm_selected_action = None
                st.rerun()

            # Cancel delete
            if col2.button(SideBarStateMgr.STRINGS['ACTION_CANCEL'], key=f"sbsm_cancel_delete_{current_state}"):
                st.session_state.sbsm_selected_action = None
                st.rerun()

        def do_action_view_json():
            from st_ui.json_viewer import JSONViewer
            st.session_state.sbsm_selected_action = None
            JSONViewer.view_json(st.session_state)
        
        def do_action_duplicate():
            """ Duplicate the selected state """

            # Delete file and clear current state
            duplicated_state = SideBarStateMgr.duplicate_state(current_state)
            st.session_state.sbsm_current_state = duplicated_state
            
            # Set status message, clear action and rerun
            SideBarStateMgr.set_status_message(SideBarStateMgr.STRINGS['STATE_DUPLICATED_CREATED'].format(duplicated_state))
            st.session_state.sbsm_selected_action = None
            st.rerun()

            # Cancel delete
            if col2.button(SideBarStateMgr.STRINGS['ACTION_CANCEL'], key=f"sbsm_cancel_delete_{current_state}"):
                st.session_state.sbsm_selected_action = None
                st.rerun()

        # Render
        with st.sidebar:

            # Custom styling for actions
            st.markdown("""
                <style>
                        
                /* The custom actions box */ 
                .st-key-custom_action_container {
                    border: 2px solid white;
                    padding: 20px;
                    border-radius: .5rem;
                    background-color: white;
                }
                
                /* Get rid of the little message */ 
                .st-key-custom_action_container .stTextInput {
                    width: fit-content;
                }
                
                /* Grey background for the edit input */ 
                .st-key-custom_action_container input {
                    background-color: rgb(240, 242, 246);
                }
                
                /* Hide the 'press enter to apply' */
                .st-key-sbsm_rename_state_edit div[data-testid="InputInstructions"] {
                    visibility: hidden;
                }

                /* Make the action title underline fit & match */  
                .st-key-custom_action_container hr {
                    width: 90%;
                    background-color: rgb(227 231 241);
                }
                        
            </style>
            """, unsafe_allow_html=True)

            # Container for actions and related widgets
            action_container = st.container(key='custom_action_container')
            with action_container:
                
                # Our actions
                new_session_action = SideBarStateMgr.STRINGS['CREATE_NEW_STATE']
                actions = [new_session_action, 'Rename', 'Delete', "Duplicate", "View JSON"]

                def on_action_select(selected_action=None):
                    """ Handle action selection by setting the selected action on the key """
                    # Take the selected action from the select if not provided
                    if None == selected_action:
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
                actions_heading = SideBarStateMgr.STRINGS['ACTIONS_HEADING']
                st.subheader(actions_heading, divider='grey')
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
        SideBarStateMgr.save_state(st.session_state.sbsm_current_state, self.key_storage_map)
        
    def load_session_from_state(self, state_to_load):
        """ (re) load from the state into the current sesson """

        loaded_state = SideBarStateMgr.load_state(state_to_load, self.key_storage_map)
        SideBarStateMgr.set_session_state(self.key_storage_map, loaded_state)
        st.session_state.sbsm_current_state = state_to_load
        SideBarStateMgr.set_status_message(SideBarStateMgr.STRINGS['STATE_LOADED'].format(state_to_load))

    def get_current_state_name(self, default=''):
        return st.session_state.get('sbsm_current_state', default)

    def __init__(self, key_storage_map):  
        self.key_storage_map = key_storage_map

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

def main():
    
    # Wide is best
    st.set_page_config(layout="wide")
    
    # Setup state manager - specify state keys to persist
    key_storage_map = { "persistant" : ['p_*'], "volatile" : ['v_*'] }
    state_manager = SideBarStateMgr(key_storage_map)

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
    main()