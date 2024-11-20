"YAML helpers for loading configuration"
import os
from typing import Dict, Any
import copy
from functools import reduce
import yaml

class YAMLKeyResolver:
    """ Handles special keys in loaded YAML that allow efficient use of templates """

    def __init__(self):
        self.key_prefix = '$'
        self.ref_key = f'{self.key_prefix}ref'
        self.allof_key = f'{self.key_prefix}allOf'
        self.resolution_path = []

    @staticmethod
    def _merge_nested(target, source):
        """ Merge soure into target - source should be merged into target overwriting equivalent
        existing data in target but preserving data in target if there is no
        equivalent data in source
        """
        if isinstance(source, dict):
            for key, value in source.items():
                if key not in target:
                    target[key] = copy.deepcopy(value)
                elif isinstance(value, dict) and isinstance(target[key], dict):
                    target[key] = YAMLKeyResolver._merge_nested(target[key], value)
                elif isinstance(value, dict) and isinstance(target[key], list):
                    target[key] = copy.deepcopy(value)
                elif isinstance(value, list) and isinstance(target[key], dict):
                    target[key] = copy.deepcopy(value)
                else:
                    target[key] = value

        elif isinstance(source, list):
            if not isinstance(target, list):
                target.clear()
                target = copy.deepcopy(source)
            else:
                target.extend(copy.deepcopy(source))
        else:
            target = source
        # Done
        return target

    def _get_by_path(self, obj, path):
        """Retrieve a value from a nested dictionary using a path string."""
        try:
            sequence = path.split('/')[1:]
            reduced = reduce(lambda d, key: d[key], sequence, obj)
            return reduced
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Invalid reference path: {path}") from exc

    def _handle_allof_key(self, ref_value, resolved_value, container_dict, data):
        """ Handle the ref key """
        if isinstance(resolved_value, dict):
            container_dict = YAMLKeyResolver._merge_nested(
                container_dict,
                self._resolve_recursive(resolved_value, data))
        else:
            value_type = type(resolved_value)
            err_msg = f"'{self.allof_key}' supports dict only. '{ref_value}' was '{value_type}'"
            raise ValueError(err_msg)

        return container_dict

    def _handle_ref_key(self, ref_value, resolved_value, container_dict, data):
        """ Handle the ref key """
        if isinstance(resolved_value, dict):
            container_dict.update(self._resolve_recursive(resolved_value, data))
        else:
            value_type = type(resolved_value)
            err_msg = f"'{self.ref_key}' only supports dict types. '{ref_value}' was '{value_type}'"
            raise ValueError(err_msg)

        return container_dict

    def _handle_special_key(self, value, container_dict, data, key):
        """ Handle one of the special keys """

        # Singleton or list
        if isinstance(value, str):
            ref_values = [value]
        elif isinstance(value, list):
            ref_values = value
        else:
            err_msg = f"Reference value '{value}' should be a single or list of reference strings"
            raise ValueError(err_msg)

        # Loop through references
        for ref_value in ref_values:

            # Check valid format
            if not (isinstance(ref_value, str) and ref_value.startswith('#/')):
                err_msg = f"Reference path '{ref_value}' should be a string starting with '#/'"
                raise ValueError(err_msg)

            # Check circular dependency
            if ref_value in self.resolution_path:
                raise ValueError(f"Circular reference detected: {ref_value}")
            self.resolution_path.append(ref_value)

            try:

                # Look up the reference
                resolved_value = self._get_by_path(data, ref_value)

                # Handle the special keys
                if key == self.ref_key:
                    self._handle_ref_key(ref_value, resolved_value, container_dict, data)
                elif key == self.allof_key:
                    self._handle_allof_key(ref_value, resolved_value, container_dict, data)
                else:
                    raise ValueError(f"unkown special key '{key}'")

            finally:

                # Remove from circular dependency check
                self.resolution_path.pop()

        return container_dict

    def _resolve_recursive(self, obj, data):
        """Recursively resolve references in the given object."""
        if isinstance(obj, dict):
            new_dict = {}
            for key, value in obj.items():
                if key.startswith(self.key_prefix):

                    # Handle reference key
                    new_dict = self._handle_special_key(value, new_dict, data, key)
                else:
                    # For non-reference keys, recursively resolve the value
                    resolved = self._resolve_recursive(value, data)
                    if key not in new_dict:
                        new_dict[key] = resolved
                    elif not isinstance(resolved, dict):
                        new_dict[key] = resolved
                    else:
                        new_dict[key] = self._merge_nested(new_dict[key] , resolved)

            # Done
            return new_dict

        if isinstance(obj, list):
            # Recursively resolve each item in the list
            return [self._resolve_recursive(item, data) for item in obj]
        else:
            # For primitive types, return as is
            return obj

    def resolve(self, data):
        """ Resolve all the custom keys in the object and return a new object """

        # Start resolution with a deep copy of the data to avoid modifying the original
        return self._resolve_recursive(copy.deepcopy(data), data)

    @staticmethod
    def resolve_refs(data):
        """Resolve all references in the given data structure."""
        resolver = YAMLKeyResolver()
        return resolver.resolve(data)

class YAMLUtils:
    """ Loading and manipultaing YAML files, also custom features like includes """
    @staticmethod
    def load_yaml_with_includes(file_path: str, include_lib_path: str) -> Dict[Any, Any]:
        """ Load the file and process include statements to include local or lib include files"""

        # Open the file
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Split into lins
        lines = content.split('\n')
        processed_lines = []

        # Loop, process includes statements
        for line in lines:
            if line.strip().startswith('#!local_include'):
                include_lines = YAMLUtils._process_local_include(line, os.path.dirname(file_path))
                processed_lines.extend(include_lines)
            elif line.strip().startswith('#!lib_include'):
                include_lines = YAMLUtils._process_lib_include(line, include_lib_path)
                processed_lines.extend(include_lines)
            else:
                processed_lines.append(line)

        # Join back together and then YAML parse
        processed_content = '\n'.join(processed_lines)
        return yaml.safe_load(processed_content)

    @staticmethod
    def load_yaml(file_path: str, include_lib_path: str) -> Dict[Any, Any]:
        """ Load the yaml with includes and reference resolution """

        data = YAMLUtils.load_yaml_with_includes(file_path, include_lib_path)
        data =  YAMLKeyResolver.resolve_refs(data)
        return data

    @staticmethod
    def _process_local_include(line: str, current_dir: str) -> list:
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"Invalid local include directive: {line}")

        include_file = parts[1]
        if any(sep in include_file for sep in (os.path.sep, os.path.altsep) if sep):
            raise ValueError(f"Local include must not contain path separators: {include_file}")

        include_path = os.path.join(current_dir, include_file)
        if not os.path.exists(include_path):
            raise FileNotFoundError(f"Local include file not found: {include_path}")

        return YAMLUtils._load_file_content(include_path)

    @staticmethod
    def _process_lib_include(line: str, include_lib_path: str) -> list:
        include_lib_path = os.path.normpath(include_lib_path)
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"Invalid library include directive: {line}")

        include_path = parts[1]
        # Replace forward slashes with os-specific separator
        include_path = include_path.replace('/', os.path.sep)
        normalized_path = os.path.normpath(include_path)

        # Check no parent dir navigatio
        if '..' in normalized_path.split(os.path.sep):
            err_msg = f"Path must not navigate outside the library path: '{include_path}'"
            raise ValueError(err_msg)

        # Check path is in the include lib path
        full_path = os.path.normpath(os.path.join(include_lib_path, include_path))
        common_path = os.path.commonpath([full_path, include_lib_path])
        if not common_path == include_lib_path:
            err_msg = f"Path must not be outside the library path: '{include_path}'"
            raise ValueError(err_msg)

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Library include file not found: '{full_path}'")

        return YAMLUtils._load_file_content(full_path)

    @staticmethod
    def _load_file_content(file_path: str) -> list:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().split('\n')
