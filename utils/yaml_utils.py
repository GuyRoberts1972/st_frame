"YAML helpers for loading configuration"
import yaml
import os
from typing import Dict, Any

class YamlUtils:
    @staticmethod
    def load_yaml_with_includes(file_path: str, include_lib_path: str) -> Dict[Any, Any]:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        lines = content.split('\n')
        processed_lines = []

        for line in lines:
            if line.strip().startswith('#!local_include'):
                processed_lines.extend(YamlUtils._process_local_include(line, os.path.dirname(file_path)))
            elif line.strip().startswith('#!lib_include'):
                processed_lines.extend(YamlUtils._process_lib_include(line, include_lib_path))
            else:
                processed_lines.append(line)

        processed_content = '\n'.join(processed_lines)
        return yaml.safe_load(processed_content)

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

        return YamlUtils._load_file_content(include_path)

    @staticmethod
    def _process_lib_include(line: str, include_lib_path: str) -> list:
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"Invalid library include directive: {line}")

        include_path = parts[1]
        # Replace forward slashes with os-specific separator
        include_path = include_path.replace('/', os.path.sep)
        normalized_path = os.path.normpath(include_path)
        
        if '..' in normalized_path.split(os.path.sep):
            raise ValueError(f"Library include must not navigate outside the library path: {include_path}")

        full_path = os.path.normpath(os.path.join(include_lib_path, include_path))
        if not os.path.commonpath([full_path, include_lib_path]) == include_lib_path:
            raise ValueError(f"Library include must not navigate outside the library path: {include_path}")

        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Library include file not found: {full_path}")

        return YamlUtils._load_file_content(full_path)

    @staticmethod
    def _load_file_content(file_path: str) -> list:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().split('\n')
