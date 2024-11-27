# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
import tempfile
import os
from utils.storage_utils import LocalStorageBackend

class TestLocalStorageBackend(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = LocalStorageBackend(root_folder=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_and_read_binary(self):
        path = "test.bin"
        data = b"Hello, Binary!"
        self.storage.write_binary(path, data)
        result = self.storage.read_binary(path)
        self.assertEqual(result, data)

    def test_write_and_read_text(self):
        path = "test.txt"
        data = "Hello, Text!"
        self.storage.write_text(path, data)
        result = self.storage.read_text(path)
        self.assertEqual(result, data)

    def test_rename_file(self):
        path = "test.txt"
        new_path = "renamed.txt"
        data = "Rename me!"
        self.storage.write_text(path, data)
        self.storage.rename(path, new_path)
        result = self.storage.read_text(new_path)
        self.assertEqual(result, data)

    def test_delete_file(self):
        path = "test.txt"
        self.storage.write_text(path, "Delete me!")
        self.storage.delete(path)
        self.assertFalse(os.path.exists(self.storage._prep_path(path)))

    def test_list_files(self):
        paths = ["file1.txt", "file2.txt"]
        for path in paths:
            self.storage.write_text(path, "Test content")
        files = self.storage.list_files("")
        self.assertCountEqual(
            [os.path.basename(f) for f in files],
            paths,
        )

    def test_invalid_path(self):
        with self.assertRaises(FileNotFoundError):
            self.storage.read_text("../invalid.txt")

    def test_list_files_relative_paths(self):
        # Create test files in root and a subfolder
        root_file = "file1.txt"
        subfolder = "subfolder"
        subfolder_file = os.path.join(subfolder, "file2.txt")  # Use os.path.join for OS neutrality

        # Write test files
        self.storage.write_text(root_file, "Root file content")
        os.makedirs(self.storage._prep_path(subfolder), exist_ok=True)  # Ensure subfolder exists
        self.storage.write_text(subfolder_file, "Subfolder file content")

        # List files in root (non-recursive)
        files_in_root = self.storage.list_files("")
        self.assertIn(root_file.replace(os.path.sep, "/"), files_in_root)
        self.assertNotIn(subfolder_file.replace(os.path.sep, "/"), files_in_root)

        # List files in subfolder (non-recursive)
        files_in_subfolder = self.storage.list_files(subfolder)
        self.assertIn(subfolder_file.replace(os.path.sep, "/"), files_in_subfolder)

    def test_file_exists(self):
        # Write a test file
        path = "test_exists.txt"
        self.assertFalse(self.storage.file_exists(path))  # File should not exist initially
        self.storage.write_text(path, "Test content")
        self.assertTrue(self.storage.file_exists(path))  # File should exist after writing

    def test_copy_file(self):
        # Write a source file
        source_path = "source.txt"
        destination_path = "destination.txt"
        content = "This is a test file."
        self.storage.write_text(source_path, content)

        # Copy the file
        self.storage.copy(source_path, destination_path)

        # Verify both files exist and have the same content
        self.assertTrue(self.storage.file_exists(source_path))
        self.assertTrue(self.storage.file_exists(destination_path))
        self.assertEqual(self.storage.read_text(destination_path), content)

        # Copy to a new folder
        new_folder_path = "new_folder/destination.txt"
        self.storage.copy(source_path, new_folder_path)
        self.assertTrue(self.storage.file_exists(new_folder_path))
        self.assertEqual(self.storage.read_text(new_folder_path), content)

if __name__ == '__main__':
    unittest.main()
