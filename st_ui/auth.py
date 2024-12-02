"""  Authorisation and identification of users """
from abc import ABC, abstractmethod
import time
import logging
import bcrypt
import streamlit as st
from streamlit.web.server.websocket_headers import _get_websocket_headers
from utils.config_utils import ConfigStore

class AuthBase(ABC):
    """ Abstract base fo ruther authentication types """

    # The session state key to persist the aut object instance
    AUTH_INSTANCE_KEY = "AuthBase::auth_instance"

    @abstractmethod
    def is_authorized(self):
        """ Check if the current user is authorized. Must be implemented by subclasses. """

    @abstractmethod
    def get_username(self):
        """ Return the username of the authenticated user. Must be implemented by subclasses. """

    @abstractmethod
    def login_prompt(self):
        """ Display a login prompt if applicable. Must be implemented by subclasses. """

    @staticmethod
    def _get_auth_object():
        """ Factory function to initialize the appropriate Auth class. """

        # Read the type from config
        auth_type = ConfigStore.nested_get('user_auth.ui_auth_type')

        # Create the correct auth object
        if auth_type == "none":
            return NoneAuth()
        elif auth_type == "basic":
            return BasicAuth()
        elif auth_type in {"iap"}:
            return IAPAuth()
        else:
            raise ValueError(f"Unsupported auth_type: {auth_type}")

    @staticmethod
    def get_auth():
        """Get the auth object from state, else create and persist it."""

        # Check if the auth instance exists in the session state
        if AuthBase.AUTH_INSTANCE_KEY not in st.session_state:
            # Create a new auth instance using the factory method
            auth_instance = AuthBase._get_auth_object()
            st.session_state[AuthBase.AUTH_INSTANCE_KEY] = auth_instance

        # Return the auth instance from session state
        return st.session_state[AuthBase.AUTH_INSTANCE_KEY]

    @staticmethod
    def clear_auth():
        """Clear the authentication"""
        if AuthBase.AUTH_INSTANCE_KEY in st.session_state:
            del st.session_state[AuthBase.AUTH_INSTANCE_KEY]


class NoneAuth(AuthBase):
    """ Where no authentication is required - e.g. testing """
    def is_authorized(self):
        """Always return True for testing purposes."""
        return True

    def get_username(self):
        """Return a guest username."""
        return "Guest"

    def login_prompt(self):
        """No login prompt for NoneAuth."""
        st.write('No login supported.')

class IAPAuth(AuthBase):
    """ Identity aware proxy authentication

    User headers for common IAPs
    -----------------------------------------------------------
    Proxy Type               | User Header
    -----------------------------------------------------------
    Akamai EAA               | X-Akamai-EAA-User,
    Google IAP               | X-Goog-Authenticated-User-Email,
    Azure AD Proxy           | X-MS-CLIENT-PRINCIPAL-NAME,
    Okta                     | X-Okta-User,
    NGINX                    | X-User,
    AWS Cognito (ALB)        | X-Amzn-Oidc-Identity
    Generic Identity Proxies | X-User,
    -----------------------------------------------------------

    """

    def __init__(self):
        super().__init__()

        # Get the header to use
        user_header = ConfigStore.nested_get('user_auth.iap_auth_user_header')
        if user_header is None:
            raise ValueError("Missing 'user_auth.iap_auth_user_header' in config.")

        headers = _get_websocket_headers()
        if headers:
            self.username = headers.get(user_header)
        else:
            self.username = None


    def is_authorized(self):
        """ Check if the user exists """
        return self.username is not None

    def get_username(self):
        """Return the username from headers."""
        return self.username or "Unknown User"

    def login_prompt(self):
        """No login prompt for Identity-Aware Proxy authentication."""
        st.write('Authenticate via the identity aware proxy.')


class BasicAuth(AuthBase):
    """ Simple authentication from a stored user list """
    def __init__(self):
        super().__init__()

        self.credentials = ConfigStore.nested_get('user_auth.ui_user_credentials')
        if self.credentials is None:
            raise ValueError("Missing 'user_auth.ui_user_credentials' in config.")

        self.username = None
        self.authorized = False

    def is_authorized(self):
        """Check if the user has successfully logged in."""
        return self.authorized

    def get_username(self):
        """Return the username of the authenticated user."""
        return self.username

    def login_prompt(self):
        """Display a login prompt."""
        _col1, col2, _col3 = st.columns(3)

        with col2:
            st.title("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.button("Login")

            if login_button:
                try:

                    # Get the credentials stored for this user
                    user_credentials = self.credentials.get(username)
                    if user_credentials is None:
                        # Handle dotted usernames loaded from toml
                        # by splitting and navigating the nested structure
                        keys = username.split(".")
                        user_credentials = self.credentials
                        for key in keys:
                            user_credentials = user_credentials[key]

                    # Verify password with bcrypt
                    stored_password_hash = user_credentials
                    if bcrypt.checkpw(
                            password.encode('utf-8'),
                            stored_password_hash.encode('utf-8')):
                        self.username = username
                        self.authorized = True
                        st.success("Login successful!")
                        self.authorized = True
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                        logging.warning(f"failed login attempt for {username} - invalid password ")
                except (KeyError, TypeError):
                    st.error("Invalid username or password")
                    logging.warning(f"failed login attempt for {username} - invalid username ")

            # Tarpit
            time.sleep(2)

    @staticmethod
    def generate_password_hash(plain_text_password):
        """ Generate a hashed password for storage. """
        hashed = bcrypt.hashpw(plain_text_password.encode(), bcrypt.gensalt())
        return hashed.decode()  # Convert to string for storage


