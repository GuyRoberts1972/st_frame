""" The main application """
import streamlit as st
from st_ui.side_bar_state_mgr import SideBarStateMgr  
import yaml
from utils.yaml_utils import YamlUtils
import os

def load_yaml_file(file_path):

    base_dir = get_base_dir()
    include_lib_path = os.path.join(base_dir, st.secrets['paths']['templates_include_lib'])
    data = YamlUtils.load_yaml_with_includes(file_path, include_lib_path)
    return data

def get_base_dir():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return base_dir

def generate_groups(relative_path=""):
    options = {}
    
    base_dir = get_base_dir()
    full_path = os.path.join(base_dir, relative_path)
    
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        if os.path.isdir(item_path):
            meta_file = os.path.join(item_path, '_meta.yaml')
            if os.path.exists(meta_file):
                meta_data = load_yaml_file(meta_file)
                options[item] = {
                    "icon": meta_data.get("icon", ""),
                    "title": meta_data.get("title", ""),
                    "description": meta_data.get("description", "")
                }
    
    return options

def get_group_templates(subfolder, relative_path=""):
    items = {}
    base_dir = get_base_dir()
    full_path = os.path.join(base_dir, relative_path, subfolder)
    
    if not os.path.isdir(full_path):
        return items
    
    for file in os.listdir(full_path):
        if file.endswith('.yaml') and file != '_meta.yaml':
            file_path = os.path.join(full_path, file)
            item_data = load_yaml_file(file_path)
            
            # Use the filename (without extension) as the key
            item_key = os.path.splitext(file)[0]
            items[item_key] = {
                "title": item_data.get("title", ""),
                "description": item_data.get("description", ""),
                "enabled": item_data.get("enabled", False)
            }
    
    return items

def load_and_run_static_method(relative_path, class_name, method_name, *args, **kwargs):
    """ load the class from the file and run the static method with the params """
    import importlib.util

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

def handle_template_selection(template_folder):
    ''' show the use case selection if not selected '''
    
    # Early out if we have a selected use case
    if 'pdata_selected_use_case_path' in st.session_state:
        return True
 
    # Import selector
    from st_ui.option_selector import OptionSelector

    # Load the template folders
    options = generate_groups(template_folder)

    # Callback: Folder contents
    def get_sub_options(option_key):
        templates = get_group_templates(option_key, template_folder)
        return templates

    # Callback: Select
    def on_select(option_key, sub_option_key, sub_option_dict):
        st.session_state.pdata_selected_use_case_path = os.path.join(option_key, sub_option_key)
        options_selector.clear_state()
        st.rerun()

    # Callback: Cancel
    def on_cancel():
        pass

    # Render it
    options_selector = OptionSelector(options, get_sub_options, on_select, on_cancel)
    options_selector.render()

    # Not selected yet
    return False


if __name__ == '__main__':





# Define the YAML string based on the earlier dictionary configuration


    # Wide
    st.set_page_config(layout="wide")

    # Setup state manager - specify state keys to persist
    key_storage_map = { 'persistant' : ['pdata_*'], 'volatile' : ['vdata_*']}
    state_manager = SideBarStateMgr(key_storage_map)
    template_folder = st.secrets["paths"]["use_case_templates"]
    if handle_template_selection(template_folder):
        # Run the app using the YAML
        try:
            # Load the template
            relative_path = st.session_state.pdata_selected_use_case_path
            base_dir = get_base_dir()
            abs_path = os.path.normpath(os.path.join(base_dir, template_folder, relative_path)) + '.yaml'
            config = load_yaml_file(abs_path)

            # Run the method - use defaults for source file and method based on app name
            class_name = config['flow_app']
            default_app_filename = class_name.removesuffix('FlowApp').lower() + '.py'
            app_filename = config.get('flow_app_filename', default_app_filename)
            relative_path = f"flow_apps/{app_filename}"
            method_name = config.get("method_name", "run")
            load_and_run_static_method(relative_path, class_name, method_name, config, state_manager)

        except yaml.YAMLError as e:
            print(f"Error parsing YAML string: {e}")
