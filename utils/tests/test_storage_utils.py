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

    def __init__(self, methodName = "runTest"):
        super().__init__(methodName)

        self.bucket_name = "test-bucket"
        self.s3_client = None
        self.storage = None

    def set_up(self):
        """ Common setup logic """

        self.s3_client = boto3.client("s3", region_name="us-east-1")
        self.s3_client.create_bucket(Bucket=self.bucket_name)
        self.storage = S3StorageBackend(bucket_name=self.bucket_name)

    @mock_aws
    def test_001_write_and_read_text(self):
        """ Test writing and reading a text file """

        self.set_up()

        file_path = "test-folder/test-file.txt"
        content = "Hello, S3!"

        self.storage.write_text(file_path, content)
        result = self.storage.read_text(file_path)

        self.assertEqual(result, content)

    @mock_aws
    def test_s3_operations(self):
        self.set_up()

        # Create a mock S3 client
        s3_client = boto3.client('s3', region_name='us-east-1')

        # Create a mock S3 bucket
        bucket_name = 'my-test-bucket'
        s3_client.create_bucket(Bucket=bucket_name)

        # Upload a file to the mock bucket
        s3_client.put_object(Bucket=bucket_name, Key='test-file.txt', Body='Hello, World!')

        # Retrieve the file from the mock bucket
        response = s3_client.get_object(Bucket=bucket_name, Key='test-file.txt')
        content = response['Body'].read().decode('utf-8')

        # Assert the content is correct
        self.assertEqual(content, 'Hello, World!')

    @mock_aws
    def test_001_write_and_read_binary(self):
        """ Test writing and reading a binary file """
        self.set_up()
        file_path = "test-folder/test-binary.bin"
        content = b"\x00\x01\x02\x03"

        self.storage.write_binary(file_path, content)
        result = self.storage.read_binary(file_path)

        self.assertEqual(result, content)

    @mock_aws
    def test_file_exists(self):
        """ Test checking if a file exists """
        self.set_up()
        file_path = "test-folder/test-file.txt"
        self.assertFalse(self.storage.file_exists(file_path))

        self.storage.write_text(file_path, "Hello, S3!")
        self.assertTrue(self.storage.file_exists(file_path))

    @mock_aws
    def test_list_files(self):
        """ Test listing files in a folder """
        self.set_up()

        file_paths = [
            "test-folder/file1.txt",
            "test-folder/file2.txt",
            "test-folder/subfolder/file3.txt"
        ]

        for file_path in file_paths:
            self.storage.write_text(file_path, "Sample content")

        listed_files = self.storage.list_files("test-folder")
        expected_files = [
            "test-folder/file1.txt",
            "test-folder/file2.txt"
        ]

        self.assertEqual(sorted(listed_files), sorted(expected_files))

    @mock_aws
    def test_list_files_2(self):
        """ Test listing files in a folder """
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
        file_path = "test-folder/test-file.txt"
        self.storage.write_text(file_path, "Hello, S3!")

        self.assertTrue(self.storage.file_exists(file_path))

        self.storage.delete(file_path)
        self.assertFalse(self.storage.file_exists(file_path))

    @mock_aws
    def test_rename(self):
        """ Test renaming a file """
        self.set_up()
        old_path = "test-folder/old-file.txt"
        new_path = "test-folder/new-file.txt"
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
        source_path = "test-folder/source-file.txt"
        destination_path = "test-folder/destination-file.txt"
        content = "Hello, S3!"

        self.storage.write_text(source_path, content)
        self.storage.copy(source_path, destination_path)

        self.assertTrue(self.storage.file_exists(source_path))
        self.assertTrue(self.storage.file_exists(destination_path))
        self.assertEqual(self.storage.read_text(destination_path), content)


if __name__ == '__main__':
    unittest.main()
