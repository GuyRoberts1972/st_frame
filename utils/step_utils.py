""" Class hierarchy for flow steps """
import streamlit as st
from utils.langchain_utils import LangChainUtils
from utils.get_text import TxtGetter as TxtGetter
from utils.flow_utils import FlowUtils
import time

class StepConfigException(Exception):
    """ exception class for parsing errors """
    pass

# Forward def for type hint
class BaseFlowApp:
    pass

class BaseFlowStep:
    """ Common data and functions for flow steps """

    def __init__(self, name, app, defaults):
        
        # Instance data
        self.step_config = app.get_step_config(name)
        self.app = app
        self.name = name

        # Set defauts for missing values
        self.step_config.update({k: v for k, v in defaults.items() if k not in self.step_config})

        self.heading = self.step_config.get('heading', None)

        # Constants
        self.pdata_prefix = 'pdata_'
        self.vdata_prefix = 'vdata_'

    def show(self):
        """ Show the step """
        step_config = self.get_step_config()
        state_dict = self.get_app().get_state()
        self.do(step_config, state_dict)

    def get_step_config(self):
        return self.step_config
    
    def get_name(self):
        return self.name
    
    def get_app(self) -> BaseFlowApp:
        return self.app
    
    def get_output_key(self):
        return f'{self.pdata_prefix}{self.name}'
    
    def get_depends_on(self, dependency=None):
        """ Get the depends on dict or key value if key specified """

        # Return the dict if key not specified
        if dependency == None:
            dependency_dict = self.step_config.get('depends_on', None)
            if dependency_dict == None:
                dependency_dict = {}
            
            # Done - return the dict
            return dependency_dict

        # Key specified, get it from the dict.
        dependency_dict = self.get_depends_on()
        if dependency not in dependency_dict:
            raise StepConfigException(f"Problem parsing step '{self.get_name}'. Dependency '{dependency}' is not in the depends_on section")
        
        # Done - return the value
        return dependency_dict[dependency]
    
    def step_name_from_path(self, dependency_path):
        """ return the name of the step this dependency belongs to"""
        # Check format
        if not isinstance(dependency_path, str):
            step_name = self.get_name()
            raise StepConfigException(f"Problem parsing step '{step_name}', expecting a dot seperated dependency path starting with step name. Got {dependency_path}")
        
        # Take the first step part
        dependency_step = dependency_path.split('.')[0]
        return dependency_step

    def get_dependency_key(self, dependency):
        """ Get the state key this dependency is stored with """
        dependency_step_name = self.get_depends_on(dependency)
        return f'{self.pdata_prefix}{dependency_step_name}'
    
    def format_item_key(self, pdata : bool, *args):
        """ creates a unique state key, pdata true for persitable else volatile"""
        if not args:
            raise ValueError("At least one additional argument is required")
    
        if pdata:
            prefix = self.pdata_prefix
        else:
            prefix = self.vdata_prefix

        # Format and return
        key =  prefix + self.get_name() + '_' + '_'.join(args)
        return key
    
    def input_data_ready(self, state_dict):
        ''' Virtual - default: check all dependency output keys are present '''

        # Get the dependencies and check if each output is ready
        dependencies = self.get_depends_on()
        for dependency in dependencies.keys():
            dependency_path = self.get_depends_on(dependency)
            dependency_step_name = self.step_name_from_path(dependency_path)
            dependency_output_key = self.app.get_step(dependency_step_name).get_output_key()
            if None == state_dict.get(dependency_output_key):
                return False

        return True
    
    def get_output_subkeys(self):
        """ Virtual - return sub keys that will be in the output dict """
        return []

    @staticmethod
    def create_instance(class_name, **kwargs):
        """ Factory function - Create an instance of the specified class """
        
        try:
            cls = globals()[class_name]
        except KeyError:
            raise ValueError(f"Class '{class_name}' not found")

        # Check if it's a subclass of BaseClass
        if not issubclass(cls, BaseFlowStep):
            raise TypeError(f"{class_name} is not a subclass of BaseClass")

        # Create and return an instance
        return cls(**kwargs)

    
class ChooseLLMFlavour(BaseFlowStep):
    """ Choose the LLM model flavour """

    def __init__(self, name, app):

        # Defaults for this step type
        defaults = {
            'heading' : 'Choose LLM Flavour'
        }

        # Parent
        super().__init__(
            name=name, 
            app=app, 
            defaults=defaults
        )


    def do(self, step_config, state_dict):
        """ Show the LLM flavours and allow the user to select """

        text = 'Choose the chat model'
        pkey = self.format_item_key(True, 'model_select')
        chat_model_choices_list = list(LangChainUtils.get_chat_model_choices().keys())

        # Handle None pkey - default to first choice
        if None == state_dict.get(pkey):
            state_dict[pkey] = chat_model_choices_list[0]

        # Show selector
        chat_model_choice = st.selectbox(text, chat_model_choices_list, key=pkey)

        # Store the choice
        state_dict[self.get_output_key()] = chat_model_choice


class DefineInputDataStep(BaseFlowStep):
    """ Create the defined input widgets """

    def __init__(self, name, app):

        # Defaults for this step type
        defaults = {
            'heading' : 'Define the data inputs'
        }

        # Parent
        super().__init__(
            name=name, 
            app=app, 
            defaults=defaults
        )

    def do(self, step_config, state_dict):
        """ Create the widgets """

        # Get data defs
        if 'data_defs' not in step_config:
            raise StepConfigException(f"Problem parsing step {self.get_name()}. The 'data_defs' attribute is missing")
        data_defs = step_config['data_defs']

        # Loop through input items
        all_defined = True
        for item_key, item_def in data_defs.items():
            
            type = item_def['type']

            # Per item internal state keys
            pkey = self.format_item_key(True, item_key, type, 'src')
            vkey = self.format_item_key(False, item_key, type, 'src')

            # Switch on type
            if type == 'url':
                url = st.text_input(item_def["description"], key=pkey)
                item_def['src'] = url
                item_def['TxtGetter.method'] = 'from_url'
                if not url:
                    all_defined = False
                    break
            elif type == 'jira_issue':
                issue_key = st.text_input(item_def["description"], key=pkey)
                item_def['src'] = issue_key
                item_def['TxtGetter.method'] = 'from_jira_issue'
                if not issue_key:
                    all_defined = False
                    break
            elif type == 'jira_issues':
                issue_key = st.text_input(item_def["description"], key=pkey)
                item_def['src'] = issue_key
                item_def['TxtGetter.method'] = 'from_jira_issues'
                if not issue_key:
                    all_defined = False
                    break
            elif type == 'jira_jql_query':
                issue_key = st.text_input(item_def["description"], key=pkey)
                item_def['src'] = issue_key
                item_def['TxtGetter.method'] = 'from_jql_query'
                if not issue_key:
                    all_defined = False
                    break
            elif type == 'free_form_text':
                user_input = st.text_area(item_def["description"], height=150, key=pkey)
                item_def['src'] = user_input
                item_def['TxtGetter.method'] = 'from_multiline_text'
                if not user_input:
                    all_defined = False
                    break
            elif type == 'uploaded_files':
                file_types = ['pdf', 'docx', 'pptx', 'txt', 'xls', 'xlsx', 'csv']
                if None == state_dict.get(vkey):
                    temp_unique_key = vkey + str(int(time.time() * 1000000))
                    state_dict[vkey] = temp_unique_key
                else:
                    temp_unique_key = state_dict[vkey]

                uploaded_files = st.file_uploader("Choose files", type=file_types, accept_multiple_files=True, key=temp_unique_key)
                if not uploaded_files:
                    all_defined = False
                    break

                item_def['src'] = []
                for uploaded_file in uploaded_files:
                    path = FlowUtils.save_uploaded_file(uploaded_file)
                    item_def['src'].append({
                        "name": uploaded_file.name,
                        "type": uploaded_file.type,
                        "path": path,
                    })
                item_def['TxtGetter.method'] = 'from_uploaded_files'

            else:
                # We don't recognise this type
                raise StepConfigException(f"Problem parsing step '{self.get_name()}'. Unknown input type '{type}'")
        
        # If we are done, set our output key
        if all_defined:
            state_dict[self.get_output_key()] = data_defs
    
    def get_output_subkeys(self):
        """ return output sub keys"""

        # Defined in data defs config
        return self.step_config['data_defs'].keys()

class RetrieveDataStep(BaseFlowStep):
    """ Get the data """

    def __init__(self, name, app):

        # Defaults for this step type
        defaults = {
            'heading' : 'Retrieve  data'
        }

        # Parent
        super().__init__(
            name=name, 
            app=app, 
            defaults=defaults
        )

        # Our internal log key
        self.internal_log_key = f'{self.pdata_prefix}{self.name}_retrieved_data_log'
        

    def do(self, step_config, state_dict):
        """ go get the defined data """

        def format_src_as_string(item_def):
            """ Format the src as a displayable string """
            src = item_def['src']
            if item_def['type'] == 'free_form_text':
                return 'Free Form Text :' + src[:10] + '...'
            if isinstance(src, list) and all(isinstance(item, dict) for item in src):
                result = []
                for item in src:
                    if 'name' in item:
                        result.append(item['name'])
                    elif len(item) > 0:
                        result.append(next(iter(item.values())))
                    else:
                        result.append('')
                return ', '.join(result)
            else:
                return str(src)
        
        def write_to_log(log_item):
            """ append an item to the internal log """
            state_dict[self.internal_log_key].append(log_item)

        if st.button("Retrieve Data"):
            output_key = self.get_output_key()
            state_dict[output_key] = {}
            state_dict[self.internal_log_key] = []
            with st.spinner("Getting data..."):
                input_data_sources_key = self.get_dependency_key('data_sources')
                for key, item_def in state_dict[input_data_sources_key].items():
                    src = item_def['src']
                    try:
                        getter_func = getattr(TxtGetter, item_def['TxtGetter.method'])
                        text = getter_func(src)
                        state_dict[output_key][key] = text
                        display_src = format_src_as_string(item_def)
                        write_to_log(f"{display_src} {len(text)} bytes.")

                    except Exception as e:
                        write_to_log(f"Failed on '{src}' :{e}.")
                        state_dict.pop(output_key, None)
                        break

        if None != state_dict.get(self.internal_log_key):
            for log_item in state_dict[self.internal_log_key]:
                st.write(log_item)

    def get_output_subkeys(self):
        """ Return sub keys that will be in the output dict """
        # The keys are defined by our data sources
        data_sources_step_name = self.get_depends_on('data_sources')
        data_sources_step = self.app.get_step(data_sources_step_name)
        return data_sources_step.get_output_subkeys()

class SelectPromptFragmentsStep(BaseFlowStep):
    """ Select one or more prompt fragments """

    def __init__(self, name, app):

        # Defaults for this step type
        defaults = {
            'heading' : 'Choose options'
        }

        # Parent
        super().__init__(
            name=name, 
            app=app, 
            defaults=defaults
        )

    def do(self, step_config, state_dict):
        """ Create the widgets """

        # Short cuts
        fragment_options = step_config['fragment_options']
 
        # Create output key
        output_key = self.get_output_key()
        if None == state_dict.get(output_key):
            state_dict[output_key] = {}

        # Loop through options
        for item_key, item_def in fragment_options.items():
            
            # Get label, choices and peky
            label = item_def['label']
            choices = item_def['choices']
            pkey = self.format_item_key(True, item_key, 'choice')

            # Handle None pkey by setting as first choice
            choices_list = list(choices.keys())
            if None == state_dict.get(pkey):
                state_dict[pkey] = choices_list[0]

            # Display and get the choice
            choice = st.selectbox(label, choices_list, key=pkey)
            state_dict[output_key][item_key] = choices[choice]

    def get_output_subkeys(self):
        """ Return sub keys that will be in the output dict """
        return self.step_config['fragment_options'].keys()
    

class FormatPromptStep(BaseFlowStep):
    """ Format a prompt template """

    def __init__(self, name, app):

        # Defaults for this step type
        defaults = {
            'heading' : 'Format prompt template'
        }

        # Parent
        super().__init__(
            name=name, 
            app=app, 
            defaults=defaults
        )

    def do(self, step_config, state_dict):
        """ Format using the replacement """

        # Short cuts
        template = step_config['template']
        token_map = {}

        # Build the token map
        depends_on = self.get_depends_on()
        for key, path in depends_on.items():
            token_map[key] = self.pdata_prefix + path

        # Do the replacements
        formatted_prompt = FlowUtils.format_prompt(template, token_map, state_dict)
 
        # Save to output key
        state_dict[self.get_output_key()] = formatted_prompt


class ChatLoopStep(BaseFlowStep):
    """ Run a chat loop to refine a draft of something """

    def __init__(self, name, app):

        # Defaults for this step type
        defaults = {
            'heading' : 'Format prompt template'
        }

        # Parent
        super().__init__(
            name=name, 
            app=app, 
            defaults=defaults
        )

    def do(self, step_config, state_dict):
        """ Setup and run the chat loop"""

        # Get dependency
        initial_system_prompt = state_dict[self.get_dependency_key('initial_system_prompt')]
        initial_human_prompt = state_dict[self.get_dependency_key('initial_human_prompt')]
        chat_model_choice = state_dict[self.get_dependency_key('chat_model_choice')]
        chat_model = LangChainUtils.get_chat_model(chat_model_choice)

        # Get options
        retrieve_context = step_config.get("retrieve_context", True)
        hide_initial_prompt = step_config.get("hide_initial_prompt", True)
            
        def do_chat_loop(
                state_dict,
                chat_model, 
                initial_system_prompt, 
                initial_human_prompt, 
                messages_key, 
                hide_initial_prompt=True, 
                retrieve_context=False):
        
            # Init the messages key in state for history storage
            if state_dict.get(messages_key) == None:
                state_dict[messages_key] = []
            
            # Short cut
            messages = state_dict[messages_key]

            # Show prior messages
            for message in messages:
                if hide_initial_prompt: # hide the first if set
                    hide_initial_prompt = False
                else:
                    # Truncate to length to trim of retrieved context
                    length = message.get('length', len(message["content"]))
                    content = message["content"][:length]
                    st.chat_message(message["role"]).markdown(content)
            
            # Get the human prompt
            human_prompt = st.chat_input("How do you want to tweak it?")
            
            # First time through use the initial prompt
            if len(messages) == 0 and initial_human_prompt != None:
                human_prompt = initial_human_prompt

            # Submit to the model
            if human_prompt:
                # Display the prompt - if it's not the first
                if not hide_initial_prompt:
                    st.chat_message("user").markdown(human_prompt)

                # Get the length before any context is added
                human_prompt_length = len(human_prompt)

                # Get any context 
                if not hide_initial_prompt and retrieve_context:
                    human_prompt = FlowUtils.add_context_to_prompt(human_prompt)

                # Pass the message history and get the response 
                with st.spinner('...'):
                    response = LangChainUtils.chat_prompt_response(chat_model, initial_system_prompt, human_prompt, messages)

                # Show the response and add it to messages
                st.chat_message("assistant").markdown(response)

                # Update messages
                state_dict[messages_key].append({"role": "user", "content": human_prompt, "length" : human_prompt_length})
                state_dict[messages_key].append({"role": "assistant", "content": response})

            # Done
            return

        # Create output key
        output_key = self.get_output_key()

        # Internal state key
        messages_key = self.format_item_key(True, 'messages')

        # Run button
        button_text = "Run"
        if None != state_dict.get(messages_key):
            button_text = "Re-run"
        if st.button("Generate"):
            state_dict[messages_key] = []

        # If started show chat dialogue
        if None != state_dict.get(messages_key):

            # Display chat dialogue      
            do_chat_loop(
                state_dict=state_dict,
                chat_model=chat_model, 
                initial_system_prompt=initial_system_prompt, 
                initial_human_prompt=initial_human_prompt,
                messages_key=messages_key,
                hide_initial_prompt=hide_initial_prompt,
                retrieve_context=retrieve_context)

        # Done
        return 


