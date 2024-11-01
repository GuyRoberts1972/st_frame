
def setup_path():
    """ update the python path so that modules under test in this folder can import other modules in this folder """

    import os, sys

    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Get the parent directory
    parent_dir = os.path.dirname(current_dir)

    # Add the parent directory to sys.path if it's not already there
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)