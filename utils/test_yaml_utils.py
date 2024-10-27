import os
import tempfile
import shutil
import unittest
from yaml_utils import YamlUtils

class TestYamlUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.lib_dir = os.path.join(self.test_dir, 'lib')
        os.makedirs(self.lib_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_load_yaml_without_includes(self):
        content = "key: value\nlist:\n  - item1\n  - item2"
        file_path = os.path.join(self.test_dir, 'test.yaml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        result = YamlUtils.load_yaml_with_includes(file_path, self.lib_dir)
        self.assertEqual(result, {'key': 'value', 'list': ['item1', 'item2']})

    def test_load_yaml_with_local_include(self):
        include_content = "included_key: included_value"
        include_file = os.path.join(self.test_dir, 'include.yaml')
        with open(include_file, 'w', encoding='utf-8') as f:
            f.write(include_content)

        main_content = "key: value\n#!local_include include.yaml"
        main_file = os.path.join(self.test_dir, 'main.yaml')
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(main_content)

        result = YamlUtils.load_yaml_with_includes(main_file, self.lib_dir)
        self.assertEqual(result, {'key': 'value', 'included_key': 'included_value'})

    def test_load_yaml_with_lib_include(self):
        lib_content = "lib_key: lib_value"
        lib_file = os.path.join(self.lib_dir, 'lib_include.yaml')
        with open(lib_file, 'w', encoding='utf-8') as f:
            f.write(lib_content)

        main_content = "key: value\n#!lib_include lib_include.yaml"
        main_file = os.path.join(self.test_dir, 'main.yaml')
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(main_content)

        result = YamlUtils.load_yaml_with_includes(main_file, self.lib_dir)
        self.assertEqual(result, {'key': 'value', 'lib_key': 'lib_value'})

    def test_invalid_local_include(self):
        content = f"#!local_include ..{os.path.sep}invalid.yaml"
        file_path = os.path.join(self.test_dir, 'test.yaml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        with self.assertRaises(ValueError):
            YamlUtils.load_yaml_with_includes(file_path, self.lib_dir)

    def test_invalid_lib_include(self):
        content = "#!lib_include ../invalid.yaml"
        file_path = os.path.join(self.test_dir, 'test.yaml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        with self.assertRaises(ValueError):
            YamlUtils.load_yaml_with_includes(file_path, self.lib_dir)

    def test_file_not_found(self):
        content = "#!local_include non_existent.yaml"
        file_path = os.path.join(self.test_dir, 'test.yaml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        with self.assertRaises(FileNotFoundError):
            YamlUtils.load_yaml_with_includes(file_path, self.lib_dir)

    def test_load_yaml_with_lib_include_2(self):
        lib_content = "lib_key: lib_value"
        lib_file = os.path.join(self.lib_dir, 'subdir', 'lib_include.yaml')
        os.makedirs(os.path.dirname(lib_file), exist_ok=True)
        with open(lib_file, 'w', encoding='utf-8') as f:
            f.write(lib_content)

        main_content = "key: value\n#!lib_include subdir/lib_include.yaml"
        main_file = os.path.join(self.test_dir, 'main.yaml')
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(main_content)

        result = YamlUtils.load_yaml_with_includes(main_file, self.lib_dir)
        self.assertEqual(result, {'key': 'value', 'lib_key': 'lib_value'})

    def test_load_yaml_with_lib_include_3(self):
        lib_content = "lib_key: lib_value"
        lib_file = os.path.join(self.lib_dir, 'subdir', 'lib_include.yaml')
        os.makedirs(os.path.dirname(lib_file), exist_ok=True)
        with open(lib_file, 'w', encoding='utf-8') as f:
            f.write(lib_content)

        # Use forward slash in the include directive
        main_content = "key: value\n#!lib_include subdir/lib_include.yaml"
        main_file = os.path.join(self.test_dir, 'main.yaml')
        with open(main_file, 'w', encoding='utf-8') as f:
            f.write(main_content)

        result = YamlUtils.load_yaml_with_includes(main_file, self.lib_dir)
        self.assertEqual(result, {'key': 'value', 'lib_key': 'lib_value'})

if __name__ == '__main__':
    unittest.main()