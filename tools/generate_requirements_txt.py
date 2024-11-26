""" Generate python requirements.txt for the different phases"""
import os
import subprocess
from tool_utils import  ToolBase # pylint: disable=import-error

class GenerateRequirementsTxt(ToolBase):
    """ Tool class to scan for non ascii in python files """

    def __init__(self):

        super().__init__()

        # Set up arguments
        self.setup_arguments({
            "--generate": {
                "action": "store_true",  # Boolean flag
                "help": "Generate the neccesary requirements.txt"
            }
        })

    def remove_local_modules(self, requirements_txt_path):
        """ Remove entries matching local module that have added by pipreqs """

        base_path = self.get_base_path()

        # Get a list of folder names in the specified folder
        folder_names = [f.name for f in os.scandir(base_path) if f.is_dir()]

        # Open the text file and filter lines
        with open(requirements_txt_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # Filter out lines that start with any of the folder names
        filtered_lines = [
            line for line in lines if not any(line.startswith(folder) for folder in folder_names)
        ]

        # Write the output
        with open(requirements_txt_path, 'w', encoding='utf-8') as out_file:
            out_file.writelines(filtered_lines)

    def create_requirements_txt(self, folder, save_path=None):
        """ Use the list of source files to generate the requirements.txt """

        # Working directory as base path
        cwd = self.get_base_path()

        # Default save path
        if save_path is None:
            save_path = os.path.join(folder, "requirements.txt")

        # Construct the pipreqs command
        pipreqs_command = ["pipreqs", "--savepath", save_path, "--force", folder]

        try:
            # Execute the pipreqs command
            subprocess.run(pipreqs_command, check=True, cwd=cwd)
            print(f"Successfully generated '{save_path}'")
        except subprocess.CalledProcessError as e:
            print(f"Error generating requirements file: {e}")

        # Clean out local modules
        self.remove_local_modules(save_path)

    def run(self):
        """ Run the tool """

        self.setup_python_path()

        if self.get_argument_value("--generate"):
            self.create_requirements_txt('utils')
            self.create_requirements_txt('st_ui')
            self.create_requirements_txt('tools')
        else:
            print('Please specify the type of requirements to generate')
            self.print_usage()
            return False

        return True


if __name__ == "__main__":

    # Run an instance of the tool
    os._exit(GenerateRequirementsTxt().run())


