# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
import tempfile
from unittest.mock import patch
from utils.template_mgr import TemplateManager
from utils.storage_utils import LocalStorageBackend


class TestTemplateManager(unittest.TestCase):

    def setUp(self):

        self.temp_dir_1 = tempfile.TemporaryDirectory()
        self.use_case_templates_store = LocalStorageBackend(root_folder=self.temp_dir_1.name)
        self.temp_dir_2 = tempfile.TemporaryDirectory()
        self.templates_include_lib_store = LocalStorageBackend(root_folder=self.temp_dir_2.name)

    def tearDown(self):
        self.temp_dir_1.cleanup()
        self.temp_dir_2.cleanup()

    @patch('utils.template_mgr.ConfigStore')
    @patch('utils.template_mgr.StorageBackend')
    @patch('utils.template_mgr.YAMLUtils')
    def test_generate_groups(self, mock_yaml_utils, mock_storage_backend, mock_config_store):

        # Static mocks
        "file2.txt"
        mock_yaml_utils.load_yaml.return_value = {
                    "icon": 'test_icon',
                    "title": 'test_title',
                    "description": 'test_description'
                }

        # Set up dir
        paths = ["folder1/_meta.yaml", "folder2/_meta.yaml"]
        for path in paths:
            self.use_case_templates_store.write_text(path, "Test content")

        # Storage mock
        mock_storage_backend.get_storage.side_effect = [
            self.use_case_templates_store,
            self.templates_include_lib_store
            ]

        manager = TemplateManager()
        groups = manager.generate_groups()
        self.assertSetEqual({'folder1', 'folder2'}, set(groups.keys()))

    @patch('utils.template_mgr.ConfigStore')
    @patch('utils.template_mgr.StorageBackend')
    @patch('utils.template_mgr.YAMLUtils')
    def test_get_group_templates(self, mock_yaml_utils, mock_storage_backend, mock_config_store):

        # Static mocks
        mock_storage_backend.basename.return_value = 'template.yaml'
        mock_config_store.nested_get.return_value = 'test'
        mock_yaml_utils.load_yaml.return_value = {
                    "title": 'test_title',
                    "description": 'test_description',
                    "enabled" : 'test_enabled'
                }

        # Set up dir
        paths = ["folder1/template.yaml"]
        for path in paths:
            self.use_case_templates_store.write_text(path, "Test content")

        # Storage mock
        mock_storage_backend.get_storage.side_effect = [
            self.use_case_templates_store,
            self.templates_include_lib_store
            ]

        manager = TemplateManager()
        templates = manager.get_group_templates("folder1")
        self.assertSetEqual({'template'}, set(templates.keys()))


if __name__ == '__main__':
    unittest.main()
