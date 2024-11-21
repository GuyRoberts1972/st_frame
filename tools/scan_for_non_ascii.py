""" Scan the source tree looking for non git ignored python files with non ascii chars. """
import os
import chardet # pylint: disable=import-error
from tool_utils import  ToolBase # pylint: disable=import-error

class NonAsciiScanner(ToolBase):
    """ Tool class to scan for non ascii in python files """

    def check_for_non_ascii(self, relative_path):
        """ Load the file and get the module and class docstrings """

        count = 0

        # Full path
        file_path = self.full_path(relative_path)
        if not file_path.endswith('.py'):
            return count

        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                result = chardet.detect(content)
                encoding = result['encoding'] or 'utf-8'

            decoded_content = content.decode(encoding)
            lines = decoded_content.splitlines()

            for line_num, line in enumerate(lines, 1):
                for col, char in enumerate(line, 1):
                    if ord(char) > 127:  # Check if character is non-ASCII
                        location = f"{file_path}:{line_num}:{col}"
                        print(f"{location} - Non-ASCII char: {char} (Unicode: U+{ord(char):04X})")
                        print(f"Line content: {line}")
                        print("Please escape this character if it is in a string literall.")
                        print("---")
                        count = count + 1

        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            raise

        # Done
        return count

    def run(self):
        """ Run the tool """

        # Get the managed files and check them
        git_files = self.get_git_files()
        total_count = 0
        for file_path in git_files:
            total_count = total_count + self.check_for_non_ascii(file_path)

        # Non zero is failure
        print(f"{len(git_files)} files scanned, {total_count} non ascii chars found.")
        return total_count


if __name__ == "__main__":

    # Run an instance of the tool
    os._exit(NonAsciiScanner().run())
