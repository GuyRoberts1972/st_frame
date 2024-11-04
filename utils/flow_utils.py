
""" Utility methods for flows """
import streamlit as st
from utils.langchain_utils import LangChainUtils
import tempfile, os, hashlib, re
from typing import List
from urllib.parse import urlparse
from utils.get_text import TxtGetter


class FlowUtils:
    """ Static utility methods for flows """
    
    ## Non UI helpers ###

    def print_session_state_keys(title=None):
        if title:
            print(title)
        for key in st.session_state.keys():
            print(f"{key}")

    def get_temp_dir():
        ''' create and get a temp dir for file storage'''

        # Create a subdirectory in the temp directory for your app
        temp_dir = os.path.join(tempfile.gettempdir(), "FlowUtils")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        return temp_dir

    def calculate_sha256(file_content):
        """Calculate SHA256 hash of file content."""
        return hashlib.sha256(file_content).hexdigest()

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
        # Remove extra whitespace and split into words
        words = re.findall(r'\w+', text.lower())
        
        # Estimate tokens (assuming average of 1.3 tokens per word)
        estimated_tokens = int(len(words) * 1.3)
        
        return estimated_tokens
    
    @staticmethod
    def format_prompt(format_str, token_map, value_dict):
        # Find all unique tokens in the original string
        original_tokens = set(re.findall(r'\{([^{}]+)\}', format_str))

        def replace_token(match):
            """ Do the replacement """
            token = match.group(1)
            if token in token_map:
                value_path = token_map[token]
                value = FlowUtils.nested_get(value_dict, value_path)
                if value is None:
                    raise Exception(f'could not find {value_path}')
                # Remove the token from the set of original tokens
                original_tokens.discard(token)
                # Escape any curly brackets in the replacement value
                return re.sub(r'([{}])', r'\1\1', str(value))
            return match.group(0)

        result = re.sub(r'\{(\w+)\}', replace_token, format_str)
        
        # Check if there are any unreplaced tokens
        if original_tokens:
            raise Exception(f"The following tokens were not replaced: {', '.join(original_tokens)}")

        return result
    
    def add_context_to_prompt(human_prompt: str) -> str:
        """
        Parse out links and other retrievable objects and add the text to the prompt.
        
        Args:
            human_prompt (str): The original human prompt.
        
        Returns:
            str: The human prompt with added context.
        """        
        
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, human_prompt)
        
        project_list = st.secrets['atlassian']['jira_project_list'].split(',')
        jira_regex = r'\b(?:' + '|'.join(proj.strip() for proj in project_list) + r')-\d+\b'
        jira_issues = set(re.findall(jira_regex, human_prompt))

        jira_url = st.secrets['atlassian']['jira_url']
        
        url_contents = []
        for url in urls:
            parsed_url = urlparse(url)
            if parsed_url.netloc == urlparse(jira_url).netloc:
                if parsed_url.path.startswith('/browse'):
                    issue_key = parsed_url.path.split('/')[-1]
                    jira_issues.add(issue_key)
                else:
                    content = TxtGetter.from_confluence_page(url)
                    url_contents.append(f"Content from {url}:\n{content}")
            else:
                content = TxtGetter.from_url(url)
                url_contents.append(f"Content from {url}:\n{content}")
        
        if url_contents:
            human_prompt += "\n\n" + "\n\n".join(url_contents)
        
        if jira_issues:
            jira_issues_content = TxtGetter.from_jira_issues(' '.join(jira_issues))
            human_prompt += f"\n\n{jira_issues_content}"
        
        return human_prompt

 