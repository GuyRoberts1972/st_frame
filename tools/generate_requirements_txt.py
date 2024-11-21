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
            "--build": {
                "action": "store_true",  # Boolean flag
                "help": "Generate build_requirements.txt for build time dependencies."
            }
        })

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

    def run(self):
        """ Run the tool """

        if self.get_argument_value("--build"):
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


