""" The main application """
import os
import importlib.util
import yaml
import streamlit as st
from st_ui.side_bar_state_mgr import SideBarStateMgr
from st_ui.option_selector import OptionSelector
from st_ui.json_viewer import JSONViewer
from st_ui.floating_footer import FloatingFooter
from st_ui.auth import AuthBase
from utils.config_utils import ConfigStore
from utils.template_mgr import TemplateManager



def get_base_dir():
    """ Get the base directory for the app"""
    base_dir = os.getcwd()
    return base_dir

def handle_template_selection():
    ''' show the use case selection if not selected '''

    # Early out if we have a selected use case
    if None is not st.session_state.get('pdata_selected_use_case_path'):
        return True

    # Create a template manager
    template_manager = TemplateManager()
    options = template_manager.generate_groups()

    # Callback: Folder contents
    def get_sub_options(option_key):
        templates = template_manager.get_group_templates(option_key)
        return templates

    # Callback: Select
    def on_select(option_key, sub_option_key, _sub_option_dict):
        st.session_state.pdata_selected_use_case_path = f"{option_key}/{sub_option_key}"
        options_selector.clear_state()
        st.rerun()

    # Callback: Cancel
    def on_cancel():
        pass

    # Create selector and set strings
    options_selector = OptionSelector(options, get_sub_options, on_select, on_cancel)
    options_selector.STRINGS.update({
        "TITLE": "Create New Session",
        "SUB_OPTION_PROMPT": "Select your use case:",
        "ACTION_CONFIRM_BUTTON": "Confirm",
        "BACK_BUTTON": "Back",
        "SUCCESS_MESSAGE": "You selected {sub_option} from {main_option}!",
        "DISABLED_OPTION": "{option} (Coming Soon)"
    })

    # Render
    options_selector.render()

    # Not selected yet
    return False

def load_and_run_static_method(relative_path, class_name, method_name, *args, **kwargs):
    """ load the class from the file and run the static method with the params """

    # Get the directory of the current script
    base_dir = get_base_dir()

    # Construct the absolute path to the target Python file
    abs_path = os.path.normpath(os.path.join(base_dir, relative_path))

    # Get the module name from the file name
    module_name = os.path.splitext(os.path.basename(abs_path))[0]

    # Load the module specification
    spec = importlib.util.spec_from_file_location(module_name, abs_path)

    # Create the module
    module = importlib.util.module_from_spec(spec)

    # Execute the module
    spec.loader.exec_module(module)

    # Get the class from the module
    target_class = getattr(module, class_name)

    # Get the method from the class
    target_method = getattr(target_class, method_name)

    # Call the method with the provided arguments
    return target_method(*args, **kwargs)

def show_version_and_config():
    """ Show some version and config info in the footer """

    footer_text = ConfigStore.get_config_and_version_string()
    FloatingFooter.show(footer_text)

def handle_user_auth():
    """ Handle authentication - return true to proceed with rest of app """

    # Get the appropriate auth object
    auth = AuthBase.get_auth()

    # Use the auth object
    if not auth.is_authorized():
        auth.login_prompt()
        return False
    return True

def main():
    """ Main execution """

    # Wide
    st.set_page_config(page_title="Labs Platform GenAI Tool", page_icon='\U0001F411', layout="wide")

    # Check auth
    if not handle_user_auth():
        return

    # Check if we should display the JSON viewer
    json_viewer = JSONViewer()
    if not json_viewer.run():

        # Setup state manager - specify state keys to persist
        key_storage_map = { 'persistant' : ['pdata_*'], 'volatile' : ['vdata_*']}
        saved_states_dir = ConfigStore.nested_get('paths.saved_states')
        state_manager = SideBarStateMgr(key_storage_map, saved_states_dir)

        # Load template
        if handle_template_selection():
            # Template chosen - run the app using the YAML
            try:
                # Load the template
                relative_path = st.session_state.pdata_selected_use_case_path
                config = TemplateManager().load_template(relative_path)

                # Run the method - use defaults for source file and method based on app name
                class_name = config['flow_app']
                default_app_filename = class_name.removesuffix('FlowApp').lower() + '.py'
                app_filename = config.get('flow_app_filename', default_app_filename)
                relative_path = f"flow_apps/{app_filename}"
                method_name = config.get("method_name", "run")
                load_and_run_static_method(
                    relative_path=relative_path,
                    class_name=class_name,
                    method_name=method_name,
                    config=config,
                    state_manager=state_manager)

            except yaml.YAMLError as e:
                print(f"Error parsing YAML string: {e}")

    # Footer
    show_version_and_config()

if __name__ == '__main__':
    main()
