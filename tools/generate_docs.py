""" Generate documentation fron the source code """
import os
import ast
from prettytable import PrettyTable
from tool_utils import  ToolBase # pylint: disable=import-error

class DocGenerator(ToolBase):
    """ Tool class to generate documentaton """

    def __init__(self):

        super().__init__()

        # Set up arguments
        self.setup_arguments({
            "--use-markdown": {
                "action": "store_true",  # Boolean flag
                "help": "Use GitHub-Flavored Markdown for output instead of PrettyTable."
            }
        })

    def get_module_and_class_info(self, relative_path):
        """ Load the file and get the module and class docstrings """

        # Full path
        file_path = self.full_path(relative_path)

        try:

            # Load the file
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                content = file.read()

            # Parse into an asp tree
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

            # Return module and list of class doc strings
            return module_docstring.strip(), class_info

        except Exception as exc: # pylint: disable=broad-exception-caught
            err_msg = f"Error processing file {file_path}: {exc}"
            raise RuntimeError(err_msg) from exc


    def create_module_and_class_info(self):
        """ Enumerate files and get there documentation """
        git_files = self.get_git_files()
        module_dict = {}
        class_dict = {}

        for file_path in git_files:
            if file_path.endswith('.py') and not os.path.basename(file_path).startswith('test'):
                module_name = os.path.splitext(file_path.replace(os.path.sep, '.'))[0]
                module_docstring, class_info = self.get_module_and_class_info(file_path)
                module_dict[module_name] = module_docstring
                class_dict[module_name] = class_info

        # Return data in dicts
        return module_dict, class_dict

    def truncate_string(self, string, max_chars=60):
        """ Truncate a string to number of chars """
        return string[:max_chars] + "..." if len(string) > max_chars else string

    def print_module_docstring_table(self, module_dict):
        """Print the module docstrings in a PrettyTable or Markdown table."""
        if self.get_argument_value("--use-markdown"):
            # Markdown table header
            markdown_table = "| Module | Docstring |\n|--------|-----------|\n"
            for module, docstring in module_dict.items():
                truncated_docstring = self.truncate_string(docstring)
                markdown_table += f"| {module} | {truncated_docstring} |\n"
            print(markdown_table)
        else:
            # PrettyTable formatting
            table = PrettyTable()
            table.field_names = ["Module", "Docstring"]
            table.align["Module"] = "l"
            table.align["Docstring"] = "l"
            table.max_width["Docstring"] = 60

            for module, docstring in module_dict.items():
                table.add_row([module, docstring])

            print(table)

    def print_class_docstring_table(self, class_dict):
        """Print the class docstrings in a PrettyTable or Markdown table."""
        if self.get_argument_value("--use-markdown"):
            # Markdown table header
            markdown_table = "| Module | Class | Docstring |\n|--------|-------|-----------|\n"
            for module, classes in class_dict.items():
                for class_name, class_docstring in classes:
                    truncated_docstring = self.truncate_string(class_docstring)
                    markdown_table += f"| {module} | {class_name} | {truncated_docstring} |\n"
            print(markdown_table)
        else:
            # PrettyTable formatting
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

    def run(self):
        """ Run the tool """

        self.setup_python_path()

        module_dict, class_dict = self.create_module_and_class_info()

        print("Module Docstrings:")
        self.print_module_docstring_table(module_dict)

        print("\nClass Docstrings:")
        self.print_class_docstring_table(class_dict)

        # Zero is ok
        print('Docs generated')
        return 0

if __name__ == "__main__":

    # Run an instance of the tool
    os._exit(DocGenerator().run())
