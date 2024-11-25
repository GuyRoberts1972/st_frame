
""" Utility methods for flows """
import tempfile
import os
import hashlib
import re
from urllib.parse import urlparse
import streamlit as st
from utils.get_text import TxtGetter, TxtGetterHelpers
from utils.config_utils import ConfigStore


class FlowUtils:
    """ Static utility methods for flows """

    ## Non UI helpers ###
    @staticmethod
    def get_temp_dir():
        ''' create and get a temp dir for file storage'''

        # Create a subdirectory in the temp directory for your app
        temp_dir = os.path.join(tempfile.gettempdir(), "FlowUtils")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        return temp_dir

    @staticmethod
    def calculate_sha256(file_content):
        """Calculate SHA256 hash of file content."""
        return hashlib.sha256(file_content).hexdigest()

    @staticmethod
    def save_uploaded_file(uploaded_file):
        """Save uploaded file with SHA256 prefix."""
        file_content = uploaded_file.read()
        sha256_hash = FlowUtils.calculate_sha256(file_content)

        # Create new filename with SHA256 prefix
        original_filename = uploaded_file.name
        new_filename = f"{sha256_hash}_{original_filename}"

        # Save file with new name
        file_path = os.path.join(FlowUtils.get_temp_dir(), new_filename)
        with open(file_path, "wb") as f:
            f.write(file_content)

        return file_path

    @staticmethod
    def nested_get(data, keys, default=None):
        """ Get a value from a dict using dotted syntax """
        for key in keys.split('.'):
            if isinstance(data, dict):
                data = data.get(key, default)
            elif isinstance(data, st.session_state.__class__):
                data = getattr(data, key, None)
            else:
                return default
        return data

    @staticmethod
    def estimate_tokens(text):
        """ Estimate the number of LLM tokens in the text """
        # Remove extra whitespace and split into words
        words = re.findall(r'\w+', text.lower())

        # Estimate tokens (assuming average of 1.3 tokens per word)
        estimated_tokens = int(len(words) * 1.3)

        return estimated_tokens

    @staticmethod
    def format_prompt(format_str, token_map, value_dict):
        """ Format the string using a token map and a lookup dict """

        # Find all unique tokens in the original string
        original_tokens = set(re.findall(r'\{([^{}]+)\}', format_str))

        def replace_token(match):
            """ Do the replacement """
            token = match.group(1)
            if token in token_map:
                value_path = token_map[token]
                value = FlowUtils.nested_get(value_dict, value_path)
                if value is None:
                    raise KeyError(f'could not find {value_path}')
                # Remove the token from the set of original tokens
                original_tokens.discard(token)
                # Escape any curly brackets in the replacement value
                return re.sub(r'([{}])', r'\1\1', str(value))
            return match.group(0)

        result = re.sub(r'\{(\w+)\}', replace_token, format_str)

        # Check if there are any unreplaced tokens
        if original_tokens:
            raise KeyError(f"The following tokens were not replaced: {', '.join(original_tokens)}")

        return result

    @staticmethod
    def extract_urls_from_text(text) -> list:
        """ Pass in some text, returns a list of URLs extracted """
        # Extract the urls with a regex
        pattern = r'https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d{1,5})?(?:/[^"\s<>{}|\^[\]`]+)*'

        urls = list(set(re.findall(pattern, text)))
        urls.sort()
        return urls

    @staticmethod
    def add_context_to_prompt(human_prompt: str) -> str:
        """
        Parse out links and other retrievable objects and add the text to the prompt.

        Args:
            human_prompt (str): The original human prompt.

        Returns:
            str: The human prompt with added context.
        """

        # Extract the urls with a regex
        urls = FlowUtils.extract_urls_from_text(human_prompt)

        # Extract the jira issues using regex
        jira_regex = None
        jira_issues = []
        project_list = ConfigStore.nested_get(
            nested_key='atlassian.jira_project_list',
            default_value='',
            default_log_msg='skipping jira project prompt context'
            )
        project_list = TxtGetterHelpers.split_string(project_list)
        if len(project_list) > 0:
            jira_regex = r'\b(?:' + '|'.join(proj.strip() for proj in project_list) + r')-\d+\b'
            jira_issues = set(re.findall(jira_regex, human_prompt))

        # Get the base jira URL so we can spot urls to confluence / JIRA
        jira_url = ConfigStore.nested_get(
            nested_key='atlassian.jira_url',
            default_value=None,
            default_log_msg='skipping atlassian url prompt context augmentation'
            )

        # Loop on urls
        url_contents = []
        confluence_contents = []
        for url in urls:
            parsed_url = urlparse(url)

            # See if it is a wiki or jira issues link
            if jira_url is not None and parsed_url.netloc == urlparse(jira_url).netloc:
                if parsed_url.path.startswith('/browse'):

                    # Jira issue - extract from path and add to set
                    if jira_regex is not None:
                        jira_issues = jira_issues | set(re.findall(jira_regex, parsed_url.path))
                else:
                    # Confluence
                    content = TxtGetter.from_confluence_page(url)
                    confluence_contents.append(f"Content from confluence wiki {url}:\n{content}")
            else:
                # URL
                content = TxtGetter.from_url(url)
                url_contents.append(f"Content scraped from web url {url}:\n{content}")

        # Add content to the prompts
        if confluence_contents or url_contents or jira_issues:
            human_prompt += "\n\n The following text related to the above was retrieved for context.\n\n".join(confluence_contents)

        if confluence_contents:
            human_prompt += "\n\n" + "\n\n".join(confluence_contents)

        if url_contents:
            human_prompt += "\n\n" + "\n\n".join(url_contents)

        if jira_issues:
            # Sort them into a known order (for testing)
            jira_issues = list(jira_issues)
            jira_issues.sort()
            jira_issues_content = TxtGetter.from_jira_issues(' '.join(jira_issues))
            human_prompt += f"\n\n{jira_issues_content}"

        return human_prompt

