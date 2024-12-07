""" Utility class to handle browsing and loading of flow templates """
import os
import logging
from utils.yaml_utils import YAMLUtils
from utils.config_utils import ConfigStore
from utils.storage_utils import StorageBackend

class TemplateManager:
    """A class to manage YAML templates and groups."""

    def __init__(self):
        self.base_dir = os.getcwd()

        # Create the storage objects defined in config

        # Templates
        use_case_templates_path = ConfigStore.nested_get('paths.use_case_templates')
        self.use_case_templates_store = StorageBackend.get_storage(use_case_templates_path)

        # Template includes
        templates_include_lib_path = ConfigStore.nested_get('paths.templates_include_lib')
        self.templates_include_lib_store = StorageBackend.get_storage(templates_include_lib_path)

        self.yaml_utils = YAMLUtils(self.use_case_templates_store, self.templates_include_lib_store)

    def _load_yaml_file(self, file_path):
        """Load the YAML file with includes and reference resolution."""

        data = self.yaml_utils.load_yaml(file_path)
        return data

    def load_template(self, template):
        """ Load the named template """

        file_path = f'{template}.yaml'
        return self._load_yaml_file(file_path)


    def generate_groups(self):
        """Generate groups of templates for the user to start a session."""
        options = {}

        folders = self.use_case_templates_store.list_folders('')
        for folder in folders:
            meta_file = f'{folder}/_meta.yaml'
            if self.use_case_templates_store.file_exists(meta_file):
                meta_data = self._load_yaml_file(meta_file)
                options[folder] = {
                    "icon": meta_data.get("icon", ""),
                    "title": meta_data.get("title", ""),
                    "description": meta_data.get("description", "")
                }

        return options

    def get_group_templates(self, subfolder):
        """Get the templates in a specific group."""
        items = {}
        file_names = self.use_case_templates_store.list_files(subfolder)
        for file_name in file_names:
            if file_name.endswith('.yaml') and not file_name.startswith('_'):
                file_path = f"{subfolder}/{file_name}"
                item_data = self._load_yaml_file(file_path)
                if item_data:
                    # Use the filename (without extension) as the key
                    item_key = os.path.splitext(file_name)[0]
                    items[item_key] = {
                        "title": item_data.get("title", ""),
                        "description": item_data.get("description", ""),
                        "enabled": item_data.get("enabled", False)
                    }
                else:
                    logging.error(f"Could not load flow template '{file_path}'")
        # Done
        return items
