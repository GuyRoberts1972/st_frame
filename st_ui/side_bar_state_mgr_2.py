"""  A sidebar navigator that manage sessions state switches """
import streamlit as st
import json
import os
from streamlit_option_menu import option_menu



class SideBarStateMgr:
    # Class-level string table
    STRINGS = {
        'CREATE_NEW_STATE': "New",
        'NEW_STATE_BASENAME' : 'Session_{0}',
        'SAVED_STATES': "Saved:",
        'CONFIRM_RENAME': "✅",
        'CANCEL_RENAME': "❌",
        'RENAME': "✏️",
        'DELETE': "🗑️",
        'STATE_CREATED': "'{0}' created.",
        'STATE_RENAMED': "'{0}' renamed.",
        'STATE_DELETED': "'{0}' deleted.",
        'STATE_LOADED': "'{0}' loaded.",
        'DEFAULT_STATE': 'default'
    }

    # Get saved states
    saved_states_dir = st.secrets['paths']['saved_states']
    
    @staticmethod
    def get_state_path(name):
        return os.path.join(SideBarStateMgr.saved_states_dir, f"{name}.json")

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
    def save_state(name, key_storage_map):
        if not os.path.exists(SideBarStateMgr.saved_states_dir):
            os.makedirs(SideBarStateMgr.saved_states_dir)
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
    def set_session_state(key_storage_map, loaded_state):
        
        # Clear any that are persistant or volatile first
        keys = list(st.session_state.keys())
        for key in keys:
            if SideBarStateMgr.key_is_persistant(key, key_storage_map): 
                del st.session_state[key]
            elif SideBarStateMgr.key_is_volatile(key, key_storage_map): 
                del st.session_state[key]
        
        # Now set
        st.session_state.update(loaded_state)
        
    
    @staticmethod
    def get_saved_states():
        return [os.path.splitext(f)[0] for f in os.listdir(SideBarStateMgr.saved_states_dir) if f.endswith('.json')]

    @staticmethod
    def delete_state(name):
        os.remove(SideBarStateMgr.get_state_path(name))

    @staticmethod
    def rename_state(old_name, new_name):
        os.rename(SideBarStateMgr.get_state_path(old_name), SideBarStateMgr.get_state_path(new_name))

    @staticmethod
    def set_status_message(message, message_type='success'):
        st.session_state.sbsm_status_message = message
        st.session_state.sbsm_status_type = message_type

    @staticmethod
    def show_status_message():
        if 'sbsm_status_message' in st.session_state and 'sbsm_status_type' in st.session_state:
            if st.session_state.sbsm_status_type == 'success':
                st.sidebar.success(st.session_state.sbsm_status_message)
            elif st.session_state.sbsm_status_type == 'error':
                st.sidebar.error(st.session_state.sbsm_status_message)
            elif st.session_state.sbsm_status_type == 'info':
                st.sidebar.info(st.session_state.sbsm_status_message)
            del st.session_state.sbsm_status_message
            del st.session_state.sbsm_status_type
   
    @staticmethod
    def setup_sidebar(key_storage_map):
        saved_states = SideBarStateMgr.get_saved_states()
        
        # Create the state option menu
        state_menu_items = saved_states
        state_icons = ["file" for _ in saved_states]
        
        def on_select(key):
            selected = st.session_state.selected_state
            if selected in saved_states:
                if selected != st.session_state.get('sbsm_current_state'):
                    st.session_state.sbsm_state_to_load = selected
            st.rerun()

        def create_new_state():
            counter = 1
            new_state_name = SideBarStateMgr.STRINGS['NEW_STATE_BASENAME'].format(counter)
            
            while new_state_name in saved_states:
                counter += 1
                new_state_name = SideBarStateMgr.STRINGS['NEW_STATE_BASENAME'].format(counter)
            
            SideBarStateMgr.save_state(new_state_name, key_storage_map)
            st.session_state.sbsm_current_state = new_state_name
            SideBarStateMgr.set_session_state(key_storage_map, {})
            SideBarStateMgr.set_status_message(SideBarStateMgr.STRINGS['STATE_CREATED'].format(new_state_name))
            st.rerun()

        with st.sidebar:
            # Actions menu
            action_menu_items = ["New", "Rename", "Delete"]
            action_icons = ["plus-circle", "pencil-square", "trash"]

            selected_action = option_menu(
                menu_title="Actions",
                options=action_menu_items,
                icons=action_icons,
                menu_icon="gear",
                default_index=-1,  # Default is none
                key="selected_action"
            )

            # Action container
            action_container = st.container()
            action_container.markdown(
                """
                <style>
                .action-container {
                    background-color: #f0f2f6;
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 10px;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            with action_container:
                current_state = st.session_state.get('selected_state')
                if selected_action == "New":
                        del st.session_state.selected_action
                        create_new_state()
                elif selected_action == "Rename" and current_state and current_state in saved_states:
                    new_name = st.text_input('Rename:', value=current_state, key=f"sbsm_new_name_{current_state}")
                    col1, col2 = st.columns(2)
                    if col1.button(SideBarStateMgr.STRINGS['CONFIRM_RENAME'], key=f"sbsm_confirm_rename_{current_state}"):
                        SideBarStateMgr.rename_state(current_state, new_name)
                        if st.session_state.get('sbsm_current_state') == current_state:
                            st.session_state.sbsm_current_state = new_name
                        SideBarStateMgr.set_status_message(SideBarStateMgr.STRINGS['STATE_RENAMED'].format(new_name))
                        st.session_state.selected_action = "Select Action"
                        st.rerun()
                    if col2.button(SideBarStateMgr.STRINGS['CANCEL_RENAME'], key=f"sbsm_cancel_rename_{current_state}"):
                        st.session_state.selected_action = "Select Action"
                        st.rerun()
                elif selected_action == "Delete" and current_state and current_state in saved_states:
                    st.warning(f"Are you sure you want to delete '{current_state}'?")
                    col1, col2 = st.columns(2)
                    if col1.button(SideBarStateMgr.STRINGS['CONFIRM_RENAME'], key=f"sbsm_confirm_delete_{current_state}"):
                        SideBarStateMgr.delete_state(current_state)
                        if st.session_state.get('sbsm_current_state') == current_state:
                            st.session_state.sbsm_current_state = None
                        SideBarStateMgr.set_status_message(SideBarStateMgr.STRINGS['STATE_DELETED'].format(current_state))
                        st.session_state.selected_action = "Select Action"
                        st.rerun()
                    if col2.button(SideBarStateMgr.STRINGS['CANCEL_RENAME'], key=f"sbsm_cancel_delete_{current_state}"):
                        st.session_state.selected_action = "Select Action"
                        st.rerun()

            # State menu
            if len(state_menu_items) > 0:
                selected = option_menu(
                    menu_title="States",
                    options=state_menu_items,
                    icons=state_icons,
                    menu_icon="hdd-stack",
                    default_index=0,
                    key="selected_state",
                    on_change=on_select
                )

            # Show status message at the bottom of the sidebar
            SideBarStateMgr.show_status_message()

    def save_current_state(self):
        # Default current state if not set
        if not st.session_state.sbsm_current_state:
            st.session_state.sbsm_current_state = SideBarStateMgr.STRINGS['DEFAULT_STATE']
        
        # Save it
        SideBarStateMgr.save_state(st.session_state.sbsm_current_state, self.key_storage_map)
    
    def __init__(self, key_storage_map):  
        self.key_storage_map = key_storage_map

        # Handle state loading at the beginning of the script
        if 'sbsm_state_to_load' in st.session_state:
            loaded_state = SideBarStateMgr.load_state(st.session_state.sbsm_state_to_load, key_storage_map)
            SideBarStateMgr.set_session_state(key_storage_map, loaded_state)
            st.session_state.sbsm_current_state = st.session_state.sbsm_state_to_load
            SideBarStateMgr.set_status_message(SideBarStateMgr.STRINGS['STATE_LOADED'].format(st.session_state.sbsm_state_to_load))
            del st.session_state.sbsm_state_to_load
        
        if 'sbsm_current_state' not in st.session_state:
            st.session_state.sbsm_current_state = None

        if 'sbsm_renaming_state' not in st.session_state:
            st.session_state.sbsm_renaming_state = None

        # Setup the side bar
        SideBarStateMgr.setup_sidebar(key_storage_map)

def main():
    
    # Wide is best
    st.set_page_config(layout="wide")
    
    # Setup state manager - specify state keys to persist
    key_storage_map = { "persistant" : ['count'], "volatile" : [] }
    state_manager = SideBarStateMgr(key_storage_map)

    st.title("Example App To Demo State Manager")

    if 'count' not in st.session_state:
        st.session_state.count = 0

    if st.button("Increment"):
        st.session_state.count += 1
        state_manager.save_current_state()
      
    st.write(f"Count: {st.session_state.count}")

if __name__ == "__main__":
    main()