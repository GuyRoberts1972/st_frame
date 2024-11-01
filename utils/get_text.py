"Retrievers to get LLM ready text from different sources"
import requests
from bs4 import BeautifulSoup
import PyPDF2
import docx
from pptx import Presentation
import pandas as pd
import os
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
import streamlit as st
import re
import json
import textwrap

class TxtGetterHelpers:
    """ helpers """

    @staticmethod
    def split_string(input_string):
        # Use regular expression to split the string
        # \s+ matches one or more whitespace characters
        # ,\s* matches a comma followed by zero or more whitespace characters
        parts = re.split(r'[,\s]+', input_string.strip())
        parts = [item for item in parts if item != ""]
        return parts

    @staticmethod
    def get_nested_value(obj, path, default="N/A"):
        keys = path.split('.')
        for key in keys:
            if obj is None:
                return default
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                return default
        return obj if obj is not None else default



class TxtGetter:

    EXTRACTORS = {
        "application/pdf": lambda file: TxtGetter.from_pdf(file),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": lambda file: TxtGetter.from_docx(file),
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": lambda file: TxtGetter.from_pptx(file),
        "text/plain": lambda file: TxtGetter.from_txt(file),
        "application/vnd.ms-excel": lambda file: TxtGetter.from_xls(file),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": lambda file: TxtGetter.from_xls(file)
    }

     
    @staticmethod
    def from_multiline_text(text):
        return text

    @staticmethod
    def from_pdf(file):
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text

    @staticmethod
    def from_docx(file):
        doc = docx.Document(file)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text

    @staticmethod
    def from_pptx(file):
        prs = Presentation(file)
        text = ""


        def shape_has_table(shape):
            ''' Return true of the shape has a table '''
            try:
                # No attribute no table 
                if not hasattr(shape, 'table'):  
                    return False
                # Try and enumerate - will throw exception if no table
                for _i, _row in enumerate(shape.table.rows, 1):
                    pass
            except Exception as e:
                return False

        def extract_text_from_shape(shape, indent_level=0):
            nonlocal text
            indent = "  " * indent_level

            if hasattr(shape, 'shapes'):  # Check if shape is a container
                if shape.name:
                    text += f"{indent}[Group: {shape.name}]\n"
                for sub_shape in shape.shapes:
                    extract_text_from_shape(sub_shape, indent_level + 1)
            elif shape_has_table(shape):  # Check if shape is a table
                text += f"{indent}[Table]\n"
                for i, row in enumerate(shape.table.rows, 1):
                    text += f"{indent}  Row {i}:\n"
                    for j, cell in enumerate(row.cells, 1):
                        cell_text = cell.text.strip()
                        if cell_text:
                            text += f"{indent}    Column {j}: {cell_text}\n"
            elif hasattr(shape, 'text_frame'):
                if shape.name:
                    text += f"{indent}[Shape: {shape.name}]\n"
                for i, paragraph in enumerate(shape.text_frame.paragraphs, 1):
                    if paragraph.text.strip():
                        text += f"{indent}  Paragraph {i}:\n"
                        for j, run in enumerate(paragraph.runs, 1):
                            if run.text.strip():
                                text += f"{indent}    Run {j}: {run.text.strip()}\n"
            elif hasattr(shape, 'text'):
                if shape.text.strip():
                    if shape.name:
                        text += f"{indent}[Shape: {shape.name}]: {shape.text.strip()}\n"
                    else:
                        text += f"{indent}{shape.text.strip()}\n"

        for i, slide in enumerate(prs.slides, 1):
            text += f"[Slide {i}]\n"
            for shape in slide.shapes:
                extract_text_from_shape(shape)
            text += "\n"

        return text.strip()

    @staticmethod
    def from_txt(file):
        """ from a text file """
        return file.getvalue().decode("utf-8")

    @staticmethod
    def from_xls(file):
        df = pd.read_excel(file)
        return df.to_string()

    @staticmethod
    def from_uploaded_files(uploaded_files):
        total_files = len(uploaded_files)
        extracted_text = f"Text extracted from {total_files} files\n\n"

        def get_metadata(file_path):
            stat = os.stat(file_path)
            return {
                "file_name": os.path.basename(file_path),
                "file_type": file_path.split('.')[-1],
                "file_size": stat.st_size,
                "creation_date": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        
        def format_metadata(metadata):
            formatted = "Metadata:\n"
            for key, value in metadata.items():
                formatted += f"- {key}: {value}\n"
            return formatted

        for index, uploaded_file in enumerate(uploaded_files, 1):
            file_type = uploaded_file['type']
            file_name = uploaded_file['name']
            file_path = uploaded_file['path']

            extractor = TxtGetter.EXTRACTORS.get(file_type)
            if not extractor:
                raise ValueError(f"Unsupported file format: {file_type}")

            metadata = get_metadata(file_path)
            extracted_text += f"File {index}/{total_files}:\n"
            extracted_text += format_metadata(metadata)

            file_content = extractor(file_path)
            
            # Add word count to metadata for text-based files
            if file_type not in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
                word_count = len(file_content.split())
                extracted_text += f"Word count: {word_count}\n\n"

            extracted_text += f"Content:\n{file_content}\n\n"
            extracted_text += "-" * 50 + "\n\n"

        # Done
        return extracted_text

    @staticmethod
    def from_url(src):
        ''' given a url get the text '''
        response = requests.get(src)
        soup = BeautifulSoup(response.text, 'html.parser')
        return ' '.join([p.get_text() for p in soup.find_all('p')])

    @staticmethod
    def from_jira_issue(issue_key):
        # Trim space
        issue_key = issue_key.strip()

        #  Get secrets
        secrets = st.secrets['atlassian']
        jira_url = secrets['jira_url']
        jira_api_endpoint = secrets['jira_api_endpoint']
        email = secrets['email'] 
        api_token = secrets['api_token']

        def handle_error(response, issue_key):
            ''' Raise exception on HTTP not ok '''
            if not response.ok:
                error_msg = response.reason
                error_text = f"Could not get data for '{issue_key}' '{error_msg}'"
                raise Exception(error_text)

        def get_issue_data(issue_key):
            url = f"{jira_url}{jira_api_endpoint}/issue/{issue_key}"
            auth = HTTPBasicAuth(email, api_token)
            headers = {"Accept": "application/json"}
            
            response = requests.get(url, headers=headers, auth=auth)
            handle_error(response, issue_key)
            return response.json()

        def get_issue_comments(issue_key):
            url = f"{jira_url}{jira_api_endpoint}/issue/{issue_key}/comment"
            auth = HTTPBasicAuth(email, api_token)
            headers = {"Accept": "application/json"}
            
            response = requests.get(url, headers=headers, auth=auth)
            handle_error(response, issue_key)
            return response.json()

        def format_description(description):
            formatted_text = ""
            
            def process_content(content):
                nonlocal formatted_text
                for item in content:
                    if item['type'] == 'paragraph':
                        processed_content = process_content(item['content'])
                        if processed_content is not None:
                            formatted_text += processed_content + "\n\n"
                    elif item['type'] == 'text':
                        formatted_text += item['text']
                    elif item['type'] == 'hardBreak':
                        formatted_text += "\n"
            
            if description and 'content' in description:
                process_content(description['content'])

            return formatted_text.strip()
        
        def format_issue_data(issue_data, comments_data):
            get_issue = lambda path, default="N/A": TxtGetterHelpers.get_nested_value(issue_data, path, default)
            get_comments = lambda path, default="N/A": TxtGetterHelpers.get_nested_value(comments_data, path, default)

            formatted_output = textwrap.dedent(f"""\
                Issue Key: {get_issue('key')}
                Summary: {get_issue('fields.summary')}
                Status: {get_issue('fields.status.name')}
                Priority: {get_issue('fields.priority.name')}
                Created: {get_issue('fields.created')}
                Updated: {get_issue('fields.updated')}

                Reporter: {get_issue('fields.reporter.displayName')}

                Assignee: {get_issue('fields.assignee.displayName')}

                Description:
                {format_description(get_issue('fields.description', {}))}

                Comments:
                """)

            for comment in get_comments('comments', []):
                get_comment = lambda path, default="N/A": TxtGetterHelpers.get_nested_value(comment, path, default)
                formatted_output += textwrap.dedent(f"""\
                    Author: {get_comment('author.displayName')}
                    Created: {get_comment('created')}
                    {format_description(get_comment('body', {}))}
                    """)

            formatted_output += "Linked Issues:\n"
            issuelinks = get_issue('fields.issuelinks', [])
            if issuelinks:
                for link in issuelinks:
                    get_link = lambda path, default="N/A": TxtGetterHelpers.get_nested_value(link, path, default)
                    if 'outwardIssue' in link:
                        linked_issue = link['outwardIssue']
                        get_linked = lambda path, default="N/A": TxtGetterHelpers.get_nested_value(linked_issue, path, default)
                        formatted_output += f"- {get_link('type.outward', 'Linked to')} {get_linked('key')}: {get_linked('fields.summary')}\n"
                    elif 'inwardIssue' in link:
                        linked_issue = link['inwardIssue']
                        get_linked = lambda path, default="N/A": TxtGetterHelpers.get_nested_value(linked_issue, path, default)
                        formatted_output += f"- {get_link('type.inward', 'Linked from')} {get_linked('key')}: {get_linked('fields.summary')}\n"
            else:
                formatted_output += "No linked issues found.\n"
            
            return formatted_output.strip()

        # Main execution
        issue_key = issue_key.strip()
        issue_data = get_issue_data(issue_key)
        comments_data = get_issue_comments(issue_key)
        formatted_issue = format_issue_data(issue_data, comments_data)
        return formatted_issue
    
    @staticmethod
    def from_jira_issues(issue_keys):
        " get text for multiple jira tickets "
        
        issues_keys_list = TxtGetterHelpers.split_string(issue_keys)
        text = ''
        for issue_key in issues_keys_list:
            text = text + TxtGetter.from_jira_issue(issue_key)
            text = text + "\n\n"
        
        return text

    @staticmethod
    def from_jql_query(jql_query, page_size=50, max_results=100):
        # Get secrets
        secrets = dict(st.secrets['atlassian'])

        def handle_error(response):
            if not response.ok:
                error_msg = response.reason
                error_text = f"Error executing JQL query: {error_msg}"
                raise Exception(error_text)

        def get_issues_data(jql, start_at=0, max_results=50):
            url = f"{secrets['jira_url']}{secrets['jira_api_endpoint']}/search"
            
            auth = HTTPBasicAuth(secrets['email'], secrets['api_token'])
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            payload = json.dumps({
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": [
                    "summary", "status", "priority", "created", "updated",
                    "reporter", "assignee", "description", "comment", "issuelinks"
                ]
            })
            
            response = requests.post(url, data=payload, headers=headers, auth=auth)
            handle_error(response)
            return response.json()

        def format_description(description):
            formatted_text = ""
            
            def process_content(content):
                nonlocal formatted_text
                for item in content:
                    if item['type'] == 'paragraph':
                        processed_content = process_content(item['content'])
                        if processed_content is not None:
                            formatted_text += processed_content + "\n\n"
                    elif item['type'] == 'text':
                        formatted_text += item['text']
                    elif item['type'] == 'hardBreak':
                        formatted_text += "\n"
            
            if description and 'content' in description:
                process_content(description['content'])
        
            return formatted_text.strip()

        def format_issues_data(issues_data):
            formatted_output = ""
            
            for issue in issues_data['issues']:
                get_issue = lambda path, default="N/A": TxtGetterHelpers.get_nested_value(issue, path, default)
                
                issue_text = textwrap.dedent(f"""\
                    Issue Key: {get_issue('key')}
                    Summary: {get_issue('fields.summary')}
                    Status: {get_issue('fields.status.name')}
                    Priority: {get_issue('fields.priority.name')}
                    Created: {get_issue('fields.created')}
                    Updated: {get_issue('fields.updated')}
                    Reporter: {get_issue('fields.reporter.displayName')}
                    Assignee: {get_issue('fields.assignee.displayName')}

                    Description:
                    {format_description(get_issue('fields.description', {}))}

                    Comments:
                    """)
                formatted_output += issue_text

                for comment in get_issue('fields.comment.comments', []):
                    get_comment = lambda path, default="N/A": TxtGetterHelpers.get_nested_value(comment, path, default)
                    comment_text = textwrap.dedent(f"""\
                        Author: {get_comment('author.displayName')}
                        Created: {get_comment('created')}
                        {format_description(get_comment('body', {}))}
                        """)
                    formatted_output += comment_text

                formatted_output += "Linked Issues:\n"
                for link in get_issue('fields.issuelinks', []):
                    get_link = lambda path, default="N/A": TxtGetterHelpers.get_nested_value(link, path, default)
                    if 'outwardIssue' in link:
                        linked_issue = link['outwardIssue']
                        get_linked = lambda path, default="N/A": TxtGetterHelpers.get_nested_value(linked_issue, path, default)
                        formatted_output += f"- {get_link('type.outward', 'Linked to')} {get_linked('key')}: {get_linked('fields.summary')}\n"
                    elif 'inwardIssue' in link:
                        linked_issue = link['inwardIssue']
                        get_linked = lambda path, default="N/A": TxtGetterHelpers.get_nested_value(linked_issue, path, default)
                        formatted_output += f"- {get_link('type.inward', 'Linked from')} {get_linked('key')}: {get_linked('fields.summary')}\n"
                
                formatted_output += "\n---\n"  # Separator between issues
            
            return formatted_output.strip()
        
        # Main execution with pagination
        all_issues = []
        start_at = 0

        while len(all_issues) < max_results:
            issues_data = get_issues_data(jql_query, start_at, page_size)
            all_issues.extend(issues_data['issues'])
            
            if len(issues_data['issues']) < page_size or len(all_issues) >= issues_data['total']:
                break
            
            start_at += page_size

        # Trim the results to max_results if necessary
        all_issues = all_issues[:max_results]

        # Create a new dictionary with the structure expected by format_issues_data
        formatted_data = {'issues': all_issues}
        
        formatted_issues = format_issues_data(formatted_data)
        return formatted_issues