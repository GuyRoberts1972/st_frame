# pylint: disable=missing-function-docstring, missing-module-docstring, missing-class-docstring, protected-access
import unittest
import tempfile
import os
from moto import mock_aws
import boto3
from utils.storage_utils import LocalStorageBackend, S3StorageBackend


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

class TestS3StorageBackend(unittest.TestCase):

    def __init__(self, methodName="runTest"):
        super().__init__(methodName)
        self.bucket_name = "test-bucket"
        self.folder = "test-folder"
        self.s3_client = None
        self.storage = None

    def set_up(self):
        """ Common setup logic """
        self.s3_client = boto3.client("s3", region_name="us-east-1")
        self.s3_client.create_bucket(Bucket=self.bucket_name)
        self.storage = S3StorageBackend(f"{self.bucket_name}/{self.folder}")

    @mock_aws
    def test_001_write_and_read_text(self):
        """ Test writing and reading a text file """
        self.set_up()
        file_path = "test-file.txt"
        content = "Hello, S3!"

        self.storage.write_text(file_path, content)
        result = self.storage.read_text(file_path)

        self.assertEqual(result, content)

    @mock_aws
    def test_s3_operations(self):
        self.set_up()
        s3_client = boto3.client('s3', region_name='us-east-1')

        # Upload a file to the mock bucket
        s3_client.put_object(Bucket=self.bucket_name, Key=f'{self.folder}/test-file.txt', Body='Hello, World!')

        # Retrieve the file using our storage backend
        content = self.storage.read_text('test-file.txt')

        # Assert the content is correct
        self.assertEqual(content, 'Hello, World!')

    @mock_aws
    def test_001_write_and_read_binary(self):
        """ Test writing and reading a binary file """
        self.set_up()
        file_path = "test-binary.bin"
        content = b"\x00\x01\x02\x03"

        self.storage.write_binary(file_path, content)
        result = self.storage.read_binary(file_path)

        self.assertEqual(result, content)

    @mock_aws
    def test_file_exists(self):
        """ Test checking if a file exists """
        self.set_up()
        file_path = "test-file.txt"
        self.assertFalse(self.storage.file_exists(file_path))

        self.storage.write_text(file_path, "Hello, S3!")
        self.assertTrue(self.storage.file_exists(file_path))

    @mock_aws
    def test_list_files(self):
        """ Test listing files in a folder """
        self.set_up()

        file_paths = [
            "file1.txt",
            "file2.txt",
            "subfolder/file3.txt"
        ]

        for file_path in file_paths:
            self.storage.write_text(file_path, "Sample content")

        listed_files = self.storage.list_files("")
        expected_files = [
            "file1.txt",
            "file2.txt"
        ]

        self.assertEqual(sorted(listed_files), sorted(expected_files))

    @mock_aws
    def test_list_files_2(self):
        """ Test listing files in the root folder """
        self.set_up()

        file_paths = [
            "file1.txt",
        ]

        for file_path in file_paths:
            self.storage.write_text(file_path, "Sample content")

        listed_files = self.storage.list_files("")
        expected_files = [
            "file1.txt",
        ]

        self.assertEqual(sorted(listed_files), sorted(expected_files))

    @mock_aws
    def test_delete(self):
        """ Test deleting a file """
        self.set_up()
        file_path = "test-file.txt"
        self.storage.write_text(file_path, "Hello, S3!")

        self.assertTrue(self.storage.file_exists(file_path))

        self.storage.delete(file_path)
        self.assertFalse(self.storage.file_exists(file_path))

    @mock_aws
    def test_rename(self):
        """ Test renaming a file """
        self.set_up()
        old_path = "old-file.txt"
        new_path = "new-file.txt"
        content = "Hello, S3!"

        self.storage.write_text(old_path, content)
        self.storage.rename(old_path, new_path)

        self.assertFalse(self.storage.file_exists(old_path))
        self.assertTrue(self.storage.file_exists(new_path))
        self.assertEqual(self.storage.read_text(new_path), content)

    @mock_aws
    def test_copy(self):
        """ Test copying a file """
        self.set_up()
        source_path = "source-file.txt"
        destination_path = "destination-file.txt"
        content = "Hello, S3!"

        self.storage.write_text(source_path, content)
        self.storage.copy(source_path, destination_path)

        self.assertTrue(self.storage.file_exists(source_path))
        self.assertTrue(self.storage.file_exists(destination_path))
        self.assertEqual(self.storage.read_text(destination_path), content)

class TestS3StorageBackendWithAndWithOutfolders(unittest.TestCase):

    def __init__(self, methodName="runTest"):
        super().__init__(methodName)
        self.bucket_name = "test-bucket"
        self.s3_client = None
        self.storage = None

    def set_up(self, folder=None):
        """ Common setup logic """
        self.s3_client = boto3.client("s3", region_name="us-east-1")
        self.s3_client.create_bucket(Bucket=self.bucket_name)
        if folder:
            self.storage = S3StorageBackend(f"{self.bucket_name}/{folder}")
        else:
            self.storage = S3StorageBackend(self.bucket_name)

    @mock_aws
    def test_bucket_without_folder(self):
        """ Test operations on a bucket without a subfolder """
        self.set_up()

        # Write files directly to the bucket root
        self.storage.write_text("file1.txt", "Content 1")
        self.storage.write_text("file2.txt", "Content 2")
        self.storage.write_text("subfolder/file3.txt", "Content 3")

        # List files in the bucket root
        listed_files = self.storage.list_files("")
        expected_files = ["file1.txt", "file2.txt"]
        self.assertEqual(sorted(listed_files), sorted(expected_files))

        # Read a file from the bucket root
        content = self.storage.read_text("file1.txt")
        self.assertEqual(content, "Content 1")

        # Check if a file exists in the bucket root
        self.assertTrue(self.storage.file_exists("file2.txt"))
        self.assertFalse(self.storage.file_exists("nonexistent.txt"))

        # Delete a file from the bucket root
        self.storage.delete("file2.txt")
        self.assertFalse(self.storage.file_exists("file2.txt"))

        # Rename a file in the bucket root
        self.storage.rename("file1.txt", "renamed.txt")
        self.assertFalse(self.storage.file_exists("file1.txt"))
        self.assertTrue(self.storage.file_exists("renamed.txt"))

        # Copy a file in the bucket root
        self.storage.copy("renamed.txt", "copied.txt")
        self.assertTrue(self.storage.file_exists("copied.txt"))
        self.assertEqual(self.storage.read_text("copied.txt"), "Content 1")

    @mock_aws
    def test_bucket_with_and_without_folder(self):
        """ Test operations on a bucket with and without a subfolder """
        # Set up storage without a folder
        self.set_up()
        root_storage = self.storage

        # Write files to the bucket root
        root_storage.write_text("root_file.txt", "Root content")
        root_storage.write_text("folder/file_in_folder.txt", "Folder content")

        # Set up storage with a folder
        self.set_up("folder")
        folder_storage = self.storage

        # List files in the bucket root
        root_files = root_storage.list_files("")
        self.assertEqual(sorted(root_files), ["root_file.txt"])

        # List files in the folder
        folder_files = folder_storage.list_files("")
        self.assertEqual(sorted(folder_files), ["file_in_folder.txt"])

        # Read files from both storages
        self.assertEqual(root_storage.read_text("root_file.txt"), "Root content")
        self.assertEqual(folder_storage.read_text("file_in_folder.txt"), "Folder content")

        # Check file existence
        self.assertTrue(root_storage.file_exists("root_file.txt"))
        self.assertFalse(root_storage.file_exists("file_in_folder.txt"))
        self.assertTrue(folder_storage.file_exists("file_in_folder.txt"))
        self.assertFalse(folder_storage.file_exists("root_file.txt"))

if __name__ == '__main__':
    unittest.main()
