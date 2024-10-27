""" Generate documentation summaries for doc strings """
import os
import ast
import sys
import subprocess
from prettytable import PrettyTable

def get_git_files(base_path):
    try:
        result = subprocess.run(['git', 'ls-files'], 
                                cwd=base_path, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True, 
                                check=True)
        return result.stdout.splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error running git ls-files: {e}")
        return []

def get_module_and_class_info(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            content = file.read()
        tree = ast.parse(content)
        
        # Get module-level docstring
        module_docstring = ast.get_docstring(tree) or ''
        
        # Get class information
        class_info = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                class_docstring = ast.get_docstring(node) or ''
                class_info.append((class_name, class_docstring.strip()))
        
        return module_docstring.strip(), class_info
    except FileNotFoundError:
        print(f"Warning: File not found - {file_path}")
        return None, []
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        return None, []

def create_module_and_class_info(base_path):
    git_files = get_git_files(base_path)
    module_dict = {}
    class_dict = {}

    for file_path in git_files:
        if file_path.endswith('.py') and not os.path.basename(file_path).startswith('test'):
            full_path = os.path.join(base_path, file_path)
            module_name = os.path.splitext(file_path.replace(os.path.sep, '.'))[0]
            
            module_docstring, class_info = get_module_and_class_info(full_path)
            module_dict[module_name] = module_docstring
            class_dict[module_name] = class_info

    return module_dict, class_dict

def print_module_docstring_table(module_dict):
    table = PrettyTable()
    table.field_names = ["Module", "Docstring"]
    table.align["Module"] = "l"
    table.align["Docstring"] = "l"
    table.max_width["Docstring"] = 60

    for module, docstring in module_dict.items():
        table.add_row([module, docstring])

    print(table)

def print_class_docstring_table(class_dict):
    table = PrettyTable()
    table.field_names = ["Module", "Class", "Docstring"]
    table.align["Module"] = "l"
    table.align["Class"] = "l"
    table.align["Docstring"] = "l"
    table.max_width["Docstring"] = 60

    for module, classes in class_dict.items():
        for class_name, class_docstring in classes:
            table.add_row([module, class_name, class_docstring])

    print(table)

if __name__ == "__main__":
    # Get the directory of the currently executing file
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Add the base path to sys.path to allow importing modules
    sys.path.insert(0, base_path)
    
    module_dict, class_dict = create_module_and_class_info(base_path)
    
    print("Module Docstrings:")
    print_module_docstring_table(module_dict)
    
    print("\nClass Docstrings:")
    print_class_docstring_table(class_dict)