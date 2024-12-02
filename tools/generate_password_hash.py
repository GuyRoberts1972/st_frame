""" Generate a password hash for use with basic auth """
import os
from tool_utils import  ToolBase # pylint: disable=import-error
from st_ui.auth import  BasicAuth

class PasswordHashGenerato(ToolBase):
    """ Tool class to generate password hash """

    def run(self):
        """ Run the tool """

        while True:
            password = input("Enter a password to hash (or type 'exit' to quit): ")
            if password.lower() == "exit":
                break
            hashed_password = BasicAuth.generate_password_hash(password)
            print(f"Hashed Password: {hashed_password}\n")

        # Zero is ok
        print('Docs generated')
        return 0

if __name__ == "__main__":

    # Run an instance of the tool
    os._exit(PasswordHashGenerato().run())
