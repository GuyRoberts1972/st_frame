""" Storage abstraction and implementation """
from abc import ABC, abstractmethod
import os
import shutil

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
    def file_exists(self, path: str) -> bool:
        """ Check if a file exists """

    @abstractmethod
    def copy(self, source_path: str, destination_path: str) -> None:
        """ Copy a file from source to destination """


class LocalStorageBackend(StorageBackend):
    """ Local storage on the file systems """

    def __init__(self, root_folder=None):
        super().__init__()
        self.root_folder = root_folder or os.getcwd()

    def _prep_path(self, path):
        """ Prep and sanitize the path """
        full_path = os.path.join(self.root_folder, path)
        full_path = os.path.normpath(full_path)
        if ".." in full_path.split(os.path.sep):
            raise ValueError(f"Invalid path: '{full_path}'")
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

    def list_files(self, folder: str) -> list:
        """ List all files in a folder and return their relative paths """
        full_folder_path = self._prep_path(folder)
        return [
            self._to_relative_path(os.path.join(full_folder_path, f))
            for f in os.listdir(full_folder_path)
            if os.path.isfile(os.path.join(full_folder_path, f))
        ]

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
