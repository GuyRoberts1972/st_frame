
""" Utility methods for flows """
import streamlit as st
from utils.langchain_utils import LangChainUtils
import tempfile, os, hashlib, re
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
    def _nested_get(data, keys, default=None):
        for key in keys.split('.'):
            if isinstance(data, dict):
                data = data.get(key)
            elif isinstance(data, st.session_state.__class__):
                data = getattr(data, key, None)
            else:
                return default
        return data
    
    @staticmethod
    def format_prompt(format_str, token_map, value_dict):
        # Find all unique tokens in the original string
        original_tokens = set(re.findall(r'\{([^{}]+)\}', format_str))

        def replace_token(match):
            """ Do the replacement """
            token = match.group(1)
            if token in token_map:
                value_path = token_map[token]
                value = FlowUtils._nested_get(value_dict, value_path)
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
    
    def add_context_to_prompt(human_prompt):
        ''' Parse out links and other retrievable objects and add retrieved text to the prompt '''

        # Check for URLs in the human prompt
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', human_prompt)
        
        # If URLs are found and a retriever function is provided, fetch the content
        if urls:
            url_contents = []
            for url in urls:
                content = TxtGetter.from_url(url)
                url_contents.append(f"Content from {url}:\n{content}")
            
            # Append URL contents to the human prompt
            human_prompt += "\n\n" + "\n\n".join(url_contents)

        # Jira ticket regex
        project_list = st.secrets['atlassian']['jira_project_list']
        jira_regex = '|'.join(proj.strip() for proj in project_list.split(','))
        jira_regex = r'\b(?:' + jira_regex + r')-\d+\b'


        # Look for tickets, get text, add it
        jira_issues = re.findall(jira_regex, human_prompt)
        if jira_issues:
            jira_issues_content = TxtGetter.from_jira_issues(' '.join(jira_issues))
            human_prompt += "\n\n" + "\n\n".join(jira_issues_content)

        # Done
        return human_prompt