""" Common functionality for tools """
import os
import subprocess
import logging
import argparse
import sys


class ToolBase:
    """ Base class tools that provides core common functionality """

    def __init__(self):

        self.base_path = None
        self.parser = argparse.ArgumentParser(description="Process command-line arguments.")

    def setup_python_path(self):
        """ adds paths needed for application code """

        # Add the root folder
        base_path = self.get_base_path()
        sys.path.append(base_path)

    def setup_arguments(self, argument_dict):
        """
        Set up command-line arguments based on the provided dictionary.
        """
        for arg_name, options in argument_dict.items():
            self.parser.add_argument(arg_name, **options)

    def get_argument_value(self, arg_name):
        """
        Retrieve the value of a specific command-line argument.
        """
        args = self.parser.parse_args()
        # Convert argument name to attribute-style
        arg_attr = arg_name.lstrip("-").replace("-", "_")
        return getattr(args, arg_attr)

    def print_usage(self):
        """
        Print the usage information for the command-line arguments.
        """
        self.parser.print_help()

    def get_base_path(self):
        """ Gets the root of the project """

        # Cached
        if self.base_path is not None:
            return self.base_path

        # Where this file is running from
        module_path = os.path.dirname(os.path.abspath(__file__))

        # Check running from tools
        folder_name = os.path.basename(module_path)
        if folder_name != "tools":
            raise RuntimeError(f"Run this script from tools not '{folder_name}'")

        # Base path is one level up
        self.base_path = os.path.dirname(module_path)
        return self.base_path

    def full_path(self, relative_path):
        """ Return the full path form the relative path """
        full_path = os.path.join(self.get_base_path(), relative_path)
        return full_path

    def get_git_files(self, skip_missing=True):
        """ Get the files managed by git using ls-files
        Returns the relative path to the file
        if skip_missing, will warn and remove files not on disk (e.g. remove not committed)
        """
        try:
            result = subprocess.run(['git', 'ls-files'],
                                    cwd=self.base_path,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    check=True)

            # Split into relative path list
            relative_paths = result.stdout.splitlines()
            relative_paths = [os.path.join(*path.split('/')) for path in relative_paths]


            # Check the exist
            filtered_paths = []
            for relative_path in  relative_paths:

                full_path = self.full_path(relative_path)

                # Skip and warn if missing
                if not os.path.isfile(full_path) and skip_missing:
                    log_msg = f"skipping as does not exist {full_path}"
                    logging.warning(log_msg)
                else:
                    # Add to list
                    filtered_paths.append(relative_path)

        except subprocess.CalledProcessError as exc:
            err_msg = f"Error running git ls-files: {exc}"
            raise RuntimeError(err_msg) from exc

        # Done
        return filtered_paths

    def get_folders_with_python_files(self, skip_missing=True):
        """Wrapper to find top-level folders containing Python files."""

        git_files = self.get_git_files(skip_missing=skip_missing)

        # Filter for Python files
        python_files = [file for file in git_files if file.endswith('.py')]

        # Extract top-level folders
        top_level_folders = set()
        for file in python_files:
            top_folder = file.split(os.sep)[0]  # Get the first folder
            if top_folder:  # Ignore files at the root level
                top_level_folders.add(top_folder)

        return sorted(top_level_folders)  # Return sorted list for consistency
