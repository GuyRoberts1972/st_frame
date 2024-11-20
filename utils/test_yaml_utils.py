import os
import tempfile
import shutil
import unittest
from yaml_utils import YAMLUtils, YAMLKeyResolver

class TestMergeNested(unittest.TestCase):


    def test_merge_nested_dicts(self):
        target = { "k1" : "v1"}
        source = { "k1" : "v1"}
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, { "k1" : "v1"})

        target = { "k1" : "v1", "k2" : "v2"}
        source = { "k1" : "v1"}
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, { "k1" : "v1", "k2" : "v2"})

        source = { "k1" : "v1"}
        target = { "k1" : "v1", "k2" : "v2"}
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, { "k1" : "v1", "k2" : "v2"})

        source = { "k1" : "v1", "dk1" : {"k1" : "v1"}}
        target = { "k1" : "v1", "k2" : "v2"}
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, { "k1" : "v1", "k2" : "v2", "dk1" : {"k1" : "v1"}})

        source = { "k1" : "v1", "dk1" : {"k1" : "v1"}}
        target = { "k1" : "v1", "k2" : "v2", "dk1" : {"k1" : "v1.1"}}
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, { "k1" : "v1", "k2" : "v2", "dk1" : {"k1" : "v1"}})

        source = { "k1" : "v1", "dk1" : {"k2" : "v2"}}
        target = { "k1" : "v1", "k2" : "v2", "dk1" : {"k1" : "v1.1"}}
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, { "k1" : "v1", "k2" : "v2", "dk1" : {"k1" : "v1.1",  "k2" : "v2"}})

    def test_merge_value(self):
        target = 'target'
        source = 'source'
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, 'source')

    def test_merge_nested_lists(self):
        target = [1, 2, 3]
        source = [4, 5, 6]
        YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, [1, 2, 3, 4, 5, 6])

    def test_merge_nested_list_to_non_list(self):
        target = {"a": 1}
        source = [1, 2, 3]
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, [1, 2, 3])

    def test_merge_nested_deep_dict(self):
        target = {"a": {"b": {"c": 1}}}
        source = {"a": {"b": {"d": 2}}}
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, {"a": {"b": {"c": 1, "d": 2}}})

    def test_merge_nested_mixed_types(self):
        target = {"a": [1, 2], "b": {"c": 3}}
        source = {"a": {"d": 4}, "b": [5, 6]}
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, {"a": {"d": 4}, "b": [5, 6]})

    def test_merge_nested_empty_source(self):
        target = {"a": 1}
        source = {}
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, {"a": 1})

    def test_merge_nested_empty_target(self):
        target = {}
        source = {"a": 1}
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, {"a": 1})

    def test_merge_nested_none_values(self):
        target = {"a": None}
        source = {"a": 1, "b": None}
        target = YAMLKeyResolver._merge_nested(target, source)
        self.assertEqual(target, {"a": 1, "b": None})

class TestYAMLKeyResolver(unittest.TestCase):
    def setUp(self):
        self.resolver = YAMLKeyResolver()

    def test_basic(self):
        data = {
            "templates": {
                "bodyparts": {
                    "legs": 4,
                    "eyes": 2,
                    "tail": "the dict will override this",
                    "front": "ref2 will override this",
                    "dict": {"key1": "val1"}
                },
                "wheels": {
                    "front": 2,
                    "steering": 1,
                    "tail": 0,
                    "list": ['dict', 'will', 'override']
                }
            },
            "animal": {
                "legs": "ref1 will override this",
                "$ref": ["#/templates/bodyparts","#/templates/wheels"],
                "nose": "long",
                "tail": "no",
                "list": ['overridden']
            }
        }

        resolved = self.resolver.resolve(data)
        expected = {
            "legs": 4,
            "eyes": 2,
            "front": 2,
            "steering": 1,
            "nose": "long",
            "tail": "no",
            "dict": {"key1": "val1"},
            "list": ['overridden']
        }
        self.assertDictEqual(resolved['animal'], expected)

    def test_nested(self):

        data = {
            "templates": {
                "bodyparts": {
                    "legs": 4,
                    "left_foot": {
                        "big_toe": "big",
                        "middle_toe" : "override me"
                        }
                }
            },
            "animal": {
                "legs": "ref1 will override this",
                "$allOf": "#/templates/bodyparts",
                "left_foot" : {
                    "middle_toe" : "medium",
                    "pinky_toe" : "small"
                }
            }
        }

        resolved = self.resolver.resolve(data)
        expected = {
            "legs": 4,
            "left_foot" : {
                "big_toe": "big",
                "middle_toe" : "medium",
                "pinky_toe" : "small"
            }
        }
        self.assertDictEqual(resolved['animal'], expected)

    def test_invalid_reference(self):
        data = { "invalid": { "$ref": "#/nonexistent/path" } }
        with self.assertRaises(ValueError):
            self.resolver.resolve(data)
        data = { "$ref": "badpath" }
        with self.assertRaises(ValueError):
            self.resolver.resolve(data)

    def test_chained_reference(self):
        data = {
            "first": { "key": "value" },
            "second" : { "$ref" : "#/first" },
            "third" : { "$ref" : "#/second" }
        }

        expected = {
            "first": { "key": "value" },
            "second" : { "key": "value" },
            "third" : { "key": "value"}
        }
        resolved = self.resolver.resolve(data)
        self.assertDictEqual(resolved, expected)

    def test_list(self):
        data = {
            "key_value": [ 1, 2, 3],
            "key_value_copy" : { "$ref" : "#/key_value" },
        }

        with self.assertRaises(ValueError):
            resolved = self.resolver.resolve(data)


    def test_circular_reference(self):
        data = {
            "circular": {
                "$ref": "#/circular"
            }
        }
        with self.assertRaises(ValueError):
            self.resolver.resolve(data)

    def test_bad_special_key(self):
        resolver = YAMLKeyResolver()
        data = {
            "templates": {
                "example": {"value": 42}
            },
            "test": {
                "$unknown": "#/templates/example"
            }
        }
        with self.assertRaises(ValueError):
            resolved = resolver.resolve(data)


class TestYAMLUtils(unittest.TestCase):
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

        result = YAMLUtils.load_yaml_with_includes(file_path, self.lib_dir)
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

        result = YAMLUtils.load_yaml_with_includes(main_file, self.lib_dir)
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

        result = YAMLUtils.load_yaml_with_includes(main_file, self.lib_dir)
        self.assertEqual(result, {'key': 'value', 'lib_key': 'lib_value'})

    def test_invalid_local_include(self):
        content = f"#!local_include ..{os.path.sep}invalid.yaml"
        file_path = os.path.join(self.test_dir, 'test.yaml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        with self.assertRaises(ValueError):
            YAMLUtils.load_yaml_with_includes(file_path, self.lib_dir)

    def test_invalid_lib_include(self):
        content = "#!lib_include ../invalid.yaml"
        file_path = os.path.join(self.test_dir, 'test.yaml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        with self.assertRaises(ValueError):
            YAMLUtils.load_yaml_with_includes(file_path, self.lib_dir)

    def test_file_not_found(self):
        content = "#!local_include non_existent.yaml"
        file_path = os.path.join(self.test_dir, 'test.yaml')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        with self.assertRaises(FileNotFoundError):
            YAMLUtils.load_yaml_with_includes(file_path, self.lib_dir)

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

        result = YAMLUtils.load_yaml_with_includes(main_file, self.lib_dir)
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

        result = YAMLUtils.load_yaml_with_includes(main_file, self.lib_dir)
        self.assertEqual(result, {'key': 'value', 'lib_key': 'lib_value'})

if __name__ == '__main__':
    unittest.main()