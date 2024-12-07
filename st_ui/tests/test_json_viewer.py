# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
from st_ui.json_viewer import example_usage, JSONViewer

class TestJSONViewer(unittest.TestCase):
    def test_example_usage(self):

        # Call the example_usage function
        example_usage()

    def test_view_json(self):

        data = {
        "name": "Joe Blogs",
        "age": 30,
        "city": "Welwyn"
        }

        JSONViewer.view_json(data)



if __name__ == "__main__":
    unittest.main()