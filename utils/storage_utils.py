""" Storage abstraction and implementation """
from abc import ABC, abstractmethod
import os
import shutil
import boto3
from botocore.exceptions import ClientError

class StorageBackend(ABC):
    """ Abstract base class to define storage """
    @abstractmethod
    def read_binary(self, path: str) -> bytes:
        """ Read a binary file """

    @abstractmethod
    def write_binary(self, path: str, data: bytes) -> None:
        """ Write a binary file """

    @abstractmethod
    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """ Read a text file """

    @abstractmethod
    def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """ Write a text file """

    @abstractmethod
    def rename(self, old_path: str, new_path: str) -> None:
        """  Rename a file """

    @abstractmethod
    def delete(self, path: str) -> None:
        """ Delete a file """

    @abstractmethod
    def list_files(self, folder: str) -> list:
        """ List the files in the folder """

    @abstractmethod
    def list_folders(self, folder: str) -> list:
        """ List the folders in the folder """

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """ Check if a file exists """

    @abstractmethod
    def copy(self, source_path: str, destination_path: str) -> None:
        """ Copy a file from source to destination """

    @staticmethod
    def get_storage(storage_path: str):
        """ Factory method to return the correct storage class """

        # Check for S3 storage
        if storage_path.startswith("s3::"):
            storage_path = storage_path.removeprefix("s3::")
            parts = storage_path.split('|')
            if not parts[0]:
                raise ValueError("Invalid S3 storage path: bucket name is required.")
            s3_path = parts[0]
            region_name = parts[1] if len(parts) > 1 else None
            return S3StorageBackend(s3_path, region_name)

        # Check for local storage
        if storage_path.startswith("local::"):
            storage_path = storage_path.removeprefix("local::")

        # Default to local storage
        return LocalStorageBackend(storage_path)

    @staticmethod
    def dirname(storage_path: str):
        """ Remove the file name part and return the dir """
        storage_path = storage_path.replace('\\', '/')
        path_parts = storage_path.split('/')
        directory_parts = path_parts[:-1]
        directory_path = '/'.join(directory_parts)
        return directory_path

    @staticmethod
    def basename(storage_path: str):
        """ Extract and return the file name from the given path """
        storage_path = storage_path.replace('\\', '/')
        path_parts = storage_path.split('/')
        file_name = path_parts[-1] if path_parts else ''
        return file_name


class LocalStorageBackend(StorageBackend):
    """ Local storage on the file systems """

    def __init__(self, root_folder=None):
        super().__init__()
        self.root_folder = root_folder or os.getcwd()

    def _prep_path(self, path):
        """ Prep and sanitize the path """
        if ".." in path:
            raise ValueError(f"Invalid path: '{path}' - cannot contain '..' ")
        full_path = os.path.join(self.root_folder, path)
        full_path = os.path.normpath(full_path)
        return full_path

    def read_binary(self, path: str) -> bytes:
        """ Read file in binary mode """
        full_path = self._prep_path(path)
        with open(full_path, "rb") as file:
            return file.read()

    def write_binary(self, path: str, data: bytes) -> None:
        """ Write to file in binary mode """
        full_path = self._prep_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as file:
            file.write(data)

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """ Read file in text mode """
        full_path = self._prep_path(path)
        with open(full_path, "r", encoding=encoding) as file:
            return file.read()

    def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """ Write to file in text mode """
        full_path = self._prep_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding=encoding) as file:
            file.write(data)

    def rename(self, old_path: str, new_path: str) -> None:
        """ Rename a file """
        os.rename(self._prep_path(old_path), self._prep_path(new_path))

    def delete(self, path: str) -> None:
        """ Delete a file """
        os.remove(self._prep_path(path))

    def _to_relative_path(self, full_path: str) -> str:
        """ Convert an absolute path back to a relative path with consistent separators """
        relative_path = os.path.relpath(full_path, self.root_folder)
        return relative_path.replace(os.path.sep, "/")

    def _list(self, folder: str, files=True) -> list:
        """ List all files or folders in a folder and return their relative paths """
        full_folder_path = self._prep_path(folder)
        result = []

        for item_path in os.listdir(full_folder_path):
            full_path = os.path.join(full_folder_path, item_path)
            if files and os.path.isfile(full_path):
                result.append(item_path)
            elif not files and os.path.isdir(full_path):
                relative_path = self._to_relative_path(full_path)
                sub_folder = relative_path.lstrip(f'{folder}/')
                result.append(sub_folder)

        return result

    def list_files(self, folder: str) -> list:
        """ List all files in a folder and return their relative paths """
        return self._list(folder, files=True)

    def list_folders(self, folder: str) -> list:
        """ List all folders in a folder and return their relative paths """
        return self._list(folder, files=False)

    def file_exists(self, path: str) -> bool:
        """ Check if a file exists """
        full_path = self._prep_path(path)
        return os.path.exists(full_path) and os.path.isfile(full_path)

    def copy(self, source_path: str, destination_path: str) -> None:
        """ Copy a file from source to destination """
        full_source_path = self._prep_path(source_path)
        full_destination_path = self._prep_path(destination_path)
        os.makedirs(os.path.dirname(full_destination_path), exist_ok=True)
        shutil.copy2(full_source_path, full_destination_path)


class S3StorageBackend(StorageBackend):
    """ S3-based storage backend """

    def __init__(self, path, region_name=None):
        super().__init__()
        parts = path.split('/')
        self.bucket_name = parts[0]
        self.folder = '/'.join(parts[1:]) if len(parts) > 1 else ''
        self.s3_client = boto3.client('s3', region_name=region_name)
        self._check_bucket_exists()

    def _check_bucket_exists(self):
        """ Check if the S3 bucket exists """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as exc:
            err_msg = f"Bucket {self.bucket_name} does not exist or is inaccessible: {exc}"
            raise ValueError(err_msg) from exc

    def _normalize_path(self, path: str) -> str:
        """ Ensure path consistency for S3 keys """
        normalized = path.lstrip("/")
        if self.folder:
            normalized = f"{self.folder.rstrip('/')}/{normalized}"
        return normalized

    def read_binary(self, path: str) -> bytes:
        """ Read a binary file from S3 """
        key = self._normalize_path(path)
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except ClientError as exc:
            err_msg = f"Could not read file at {key}: {exc}"
            raise FileNotFoundError(err_msg) from exc

    def write_binary(self, path: str, data: bytes) -> None:
        """ Write a binary file to S3 """
        key = self._normalize_path(path)
        try:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=key, Body=data)
        except ClientError as exc:
            err_msg = f"Could not write binary data to {key}: {exc}"
            raise IOError(err_msg) from exc

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """ Read a text file from S3 """
        binary_data = self.read_binary(path)
        return binary_data.decode(encoding)

    def write_text(self, path: str, data: str, encoding: str = "utf-8") -> None:
        """ Write a text file to S3 """
        binary_data = data.encode(encoding)
        self.write_binary(path, binary_data)

    def rename(self, old_path: str, new_path: str) -> None:
        """ Rename a file in S3 (copy and delete) """
        old_key = self._normalize_path(old_path)
        new_key = self._normalize_path(new_path)
        try:
            self.copy(old_path, new_path)
            self.delete(old_path)
        except ClientError as exc:
            err_msg = f"Could not rename {old_key} to {new_key}: {exc}"
            raise IOError(err_msg) from exc

    def delete(self, path: str) -> None:
        """ Delete a file in S3 """
        key = self._normalize_path(path)
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        except ClientError as exc:
            err_msg = f"Could not delete file at {key}: {exc}"
            raise FileNotFoundError(err_msg) from exc

    def _list(self, folder: str, files=True) -> list:
        """ List files in a folder or the root if an empty string is passed """
        prefix = self._normalize_path(folder).rstrip("/") + "/" if folder else self.folder
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            if 'Contents' not in response:
                return []

            result = []
            for obj in response['Contents']:
                key = obj['Key']
                relative_path = key[len(prefix):].lstrip('/')
                path_parts = relative_path.split('/')

                # Add it if is a file in this directory
                if files and (len(path_parts) == 1) :
                    file_name = path_parts[0]
                    result.append(file_name)

                # Add if its a file in new subfolder
                elif not files and (len(path_parts) > 1) :
                    folder_name = path_parts[0]
                    if folder_name not in result:
                        result.append(folder_name)

            # Done
            return result
        except ClientError as exc:
            err_msg = f"Could not list files in folder {folder}: {exc}"
            raise IOError(err_msg) from exc

    def list_files(self, folder: str) -> list:
        """ List all files in a folder and return their relative paths """
        return self._list(folder, files=True)

    def list_folders(self, folder: str) -> list:
        """ List all folders in a folder and return their relative paths """
        return self._list(folder, files=False)

    def file_exists(self, path: str) -> bool:
        """ Check if a file exists in S3 """
        key = self._normalize_path(path)
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def copy(self, source_path: str, destination_path: str) -> None:
        """ Copy a file within S3 """
        source_key = self._normalize_path(source_path)
        destination_key = self._normalize_path(destination_path)
        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            self.s3_client.copy(copy_source, self.bucket_name, destination_key)
        except ClientError as exc:
            err_msg = f"Could not copy {source_key} to {destination_key}: {exc}"
            raise IOError(err_msg) from exc
