""" Class hierarchy for flow steps """
import streamlit as st
from abc import ABC, abstractmethod
import time
from utils.langchain_utils import LangChainUtils
from utils.get_text import TxtGetter as TxtGetter
from utils.flow_utils import FlowUtils

class StepConfigException(Exception):
    """ exception class for parsing errors """
    pass


# Forward def for type hint
class BaseFlowApp:
    pass

class BaseFlowStep_key_mgmt(ABC):
    """ Abstract class to Manage and format keys for a step """

    @abstractmethod
    def get_name(self):
        """ Abstract method to get the name of the step """
        pass

    def get_unique_key_prefix(self, pdata=True):
        """ Get the prefix for all this steps keys , pdata true for persitable else volatile """
        
        prefix = self.pdata_prefix
        if not pdata:
            prefix = self.vdata_prefix

        return f'{prefix}{self.get_name()}'
    
    def get_output_key(self):
        unique_key_prefix = self.get_unique_key_prefix()
        return f'{unique_key_prefix}_output_key'
    
    def format_internal_key(self, pdata : bool, *args):
        """ creates a unique state key, pdata true for persitable else volatile"""
        if not args:
            raise ValueError("At least one additional argument is required")
    
        # Format and return
        unique_key_prefix = self.get_unique_key_prefix(pdata)
        key =  unique_key_prefix + '_' + '_'.join(args)
        return key
    
    def get_internal_keys(self, include_pdata=True, include_vdata=True):
        """ Get a list of the current keys matching the parameters """

        # Search for keys that belong to this step
        internal_keys = []
        unique_pdata_key_prefix = self.get_unique_key_prefix(pdata=True)
        unique_vdata_key_prefix = self.get_unique_key_prefix(pdata=False)
        for st_key in st.session_state.keys():

            if include_pdata and st_key.startswith(unique_pdata_key_prefix):
                internal_keys.append(st_key)
            if include_vdata and st_key.startswith(unique_vdata_key_prefix):
                internal_keys.append(st_key)

        # Remove output key if present
        output_key = self.get_output_key()
        if output_key in internal_keys:
            internal_keys.remove(output_key)

        # Done
        return internal_keys

    def get_output_subkeys(self):
        """ Virtual - return sub keys that will be in the output dict """
        return []
    
class BaseFlowStep(BaseFlowStep_key_mgmt):
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

    def show(self, flow_state, render_step):
        """ Show the step 
        
                - step states:
                - WAITING - step can't start since it's dependent on upstream outputs
                - ENQUEUED - not started yet as not my turn
                - ACTIVE_START_ACK - started but waiting for ack button
                - ACTIVE - in progress awaiting user input or processing
                - ACTIVE_CONFIRM_ACK - Its done but waiting for user to confirm
                - DONE - next step can start 
        
        """
        
        # Short cuts
        step_config = self.get_step_config()
        step_state = self.get_app().get_state()
        flow_config = self.get_app().get_config()

        # Options 
        def get_option(option_name, default):
            option_value = FlowUtils.nested_get(flow_config, f"step_options.{option_name}", default)
            option_value = FlowUtils.nested_get(step_config, f"options.{option_name}", option_value)
            return option_value
    
        def get_step_status():
            """ Get the current status of the step """

            # Waiting for data from dependency steps
            if not self.input_data_ready(flow_state):
                return 'WAITING'
            # Waiting for previous step to be done
            elif not self.prev_step_output_data_ready(flow_state):
                return 'ENQUEUED'
            # If our data is not ready we are active
            elif not self.output_data_ready(flow_state):
                return 'ACTIVE'
            else:
                return 'DONE'
        
        # Get status now
        step_status = get_step_status()

        # Determine visibility
        opt_visibility = get_option('visibility', 'always')
        if step_status in ['ACTIVE', 'DONE'] and opt_visibility in ['showAfterActive']:
            hide = False
        elif opt_visibility in ['always']:
            hide = False
        else:
            hide = True
  
        # Determine expandability
        opt_expandability = get_option('expandability', 'expandOnlyWhenActive')
        if step_status in ['ACTIVE'] and opt_expandability in ['expandOnlyWhenActive']:
            expand = True
        else:
            expand = False

        opt_show_status_description = get_option('show_status_description', 'always')

        def format_status_description():
            """ Format a string that describes the steps status """
            
            dependency_step_headings = self.get_dependency_step_headings()
            prev_step_heading = self.get_prev_step_heading()
            status_description = f"This step is '{step_status}'"
            if step_status == 'WAITING':
                status_description = f"This step is waiting for data from the following steps '{dependency_step_headings}'"
            elif step_status == 'ENQUEUED':
                status_description = f"This step is waiting for the previous step '{prev_step_heading}' to be done."
                
            # Done
            return status_description

        # Action short cuts
        act_reset = ('Reset', lambda : self.on_reset())
        act_reset_output = ('Reset', lambda : self.on_reset(reset_internal_keys=False))
        act_view_JSON = ('View JSON', lambda : self.on_view_JSON())

        def fn_step_content():
            ''' Render the contents of the step, return available actions'''
            if step_status == 'WAITING':
                # Status Descrition 
                if opt_show_status_description in ['always', 'waitingAndEnqueuedOnly']:
                    st.write(format_status_description())
                # Actions
                actions = {}
            elif step_status == 'ENQUEUED':
                # Status Descrition 
                if opt_show_status_description in ['always', 'waitingAndEnqueuedOnly']:
                    st.write(format_status_description())
                # Actions
                actions = {}
            elif step_status == 'ACTIVE':
                # Status Description 
                if opt_show_status_description in ['always']:
                    st.write(format_status_description())
                # Do it
                self.do(step_config, step_state)
                # Actions
                actions = dict([act_reset, act_view_JSON])
            elif step_status == 'DONE':
                # Status Description 
                if opt_show_status_description in ['always']:
                    st.write(format_status_description())
                # Do it
                self.do(step_config, step_state)
                # Actions
                actions = dict([act_reset, act_reset_output, act_view_JSON])
            else:
                st.warning('This step is an unknown state')
            
            # Return the available actions
            return actions


        # Render
        render_step(
            step=self, 
            hide=hide, 
            expand=expand,
            step_status=step_status, 
            fn_step_content=fn_step_content)
            
        # Rerun if step status changed
        updated_step_status = get_step_status()
        if updated_step_status != step_status:
            st.rerun()

    def get_step_config(self):
        return self.step_config
    
    def get_name(self):
        return self.name
    
    def get_heading(self):
        return self.heading
    
    def get_app(self) -> BaseFlowApp:
        return self.app
    
    ## Action handlers
    def on_reset(self, reset_output_key=True, reset_internal_keys=True):
        
        # Clear the output key
        if reset_output_key:
            output_key = self.get_output_key()
            st.session_state[output_key] = None
        
        # Clear the internal keys
        if reset_internal_keys:
            internal_keys = self.get_internal_keys(include_pdata=True, include_vdata=True)
            for internal_key in internal_keys:
                st.session_state[internal_key] = None

    def on_view_JSON(self):

        # Gather all the steps keys into a dict 
        key_dict = {}

        # Output key
        output_key = self.get_output_key()
        if output_key in st.session_state:
            key_dict[output_key] = st.session_state[output_key]

        # Internal keys
        internal_keys = self.get_internal_keys(include_pdata=True, include_vdata=True)
        for key in internal_keys:
                key_dict[key] = st.session_state[key]

        # Show
        from st_ui.json_viewer import JSONViewer
        JSONViewer.view_json(key_dict)
    

    
    ### Dependency related methods
    
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
        """ return the name of the step this dependency belongs to """
        # Check format
        if not isinstance(dependency_path, str):
            step_name = self.get_name()
            raise StepConfigException(f"Problem parsing step '{step_name}', expecting a dot seperated dependency path starting with step name. Got {dependency_path}")
        
        # Take the first step part
        dependency_step = dependency_path.split('.')[0]
        return dependency_step
    
    def get_dependency_steps(self):
        """ Get list of step objects this step is dependent on """
        
        dependencies = self.get_depends_on()
        dep_steps = []
        for dep in dependencies.keys():
            dep_path = self.get_depends_on(dep)
            dep_step_name = self.step_name_from_path(dep_path)
            dep_step = self.app.get_step(dep_step_name)
            if dep_step not in dep_steps:
                dep_steps.append(dep_step)
        
        # Done 
        return dep_steps
    
    def get_dependency_step_names(self):
        """ Get list of step object names this step is dependent on """
        
        dep_step_names = []
        dep_steps = self.get_dependency_steps()
        for dep_step in dep_steps:
            dep_step_names.append(dep_step.get_name())
        
        # Done
        return dep_step_names
    
    def get_dependency_step_headings(self):
        """ Get list of step object headings this step is dependent on """
        
        dep_step_headings = []
        dep_steps = self.get_dependency_steps()
        for dep_step in dep_steps:
            dep_step_headings.append(dep_step.get_heading())
        
        # Done
        return dep_step_headings
    
    @staticmethod
    def subkey_from_path(dependency_path, dep_step_name):
        """ Get the subkey from this dependency path by removing the stepname - empty string if no subkey """
        return dependency_path.removeprefix(dep_step_name).removeprefix('.')
    
    def get_dependency_key(self, dependency):
        """ Get the state key this dependency is stored with """
        dependency_step_name = self.get_depends_on(dependency)
        dependency_step = self.get_app().get_step(dependency_step_name)
        return dependency_step.get_output_key()
    
    def get_prev_step(self):
        ''' Get the prvious step or None '''
        return self.get_app().get_prev_step(self.get_name())
    
    def get_prev_step_heading(self, default='No Previous Step'):
        """ Get the heading of the previous step - or return default"""
        prev_step = self.get_prev_step()
        if None == prev_step:
            return default
        return prev_step.get_heading()
    
    def prev_step_output_data_ready(self, flow_state):
        ''' Return true if the previous steps output data is ready - returns True if this is the first step '''
        prev_step = self.get_prev_step()
        if None == prev_step:
            return True
        return prev_step.output_data_ready(flow_state)
    
    def output_data_ready(self, flow_state):
        ''' returns true of the output keys exist with data '''
        output_key = self.get_output_key()
        if None == flow_state.get(output_key):
            return False
        return True
    
    def input_data_ready(self, flow_state):
        ''' Virtual - default: check all dependency output keys are present '''

        # Get the dependencies and check if each output is ready
        dep_steps = self.get_dependency_steps()
        for dep_step in dep_steps:
            if not dep_step.output_data_ready(flow_state):
                return False

        return True

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
        pkey = self.format_internal_key(True, 'model_select')
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

        # Show one input at a time
        show_all_at_once = step_config.get('show_all_at_once', True)

        # Loop through input items
        all_defined = True
        for item_key, item_def in data_defs.items():
            
            # Don't show anymore last one was not defined
            if not show_all_at_once and not all_defined:
                break

            type = item_def['type']

            # Per item internal state keys
            pkey = self.format_internal_key(True, item_key, type, 'src')
            vkey = self.format_internal_key(False, item_key, type, 'src')

            # Switch on type
            if type == 'url':
                url = st.text_input(item_def["description"], key=pkey)
                item_def['src'] = url
                item_def['TxtGetter.method'] = 'from_url'
                if not url:
                    all_defined = False
            elif type == 'jira_issue':
                issue_key = st.text_input(item_def["description"], key=pkey)
                item_def['src'] = issue_key
                item_def['TxtGetter.method'] = 'from_jira_issue'
                if not issue_key:
                    all_defined = False
            elif type == 'jira_issues':
                issue_key = st.text_input(item_def["description"], key=pkey)
                item_def['src'] = issue_key
                item_def['TxtGetter.method'] = 'from_jira_issues'
                if not issue_key:
                    all_defined = False
            elif type == 'jira_jql_query':
                issue_key = st.text_input(item_def["description"], key=pkey)
                item_def['src'] = issue_key
                item_def['TxtGetter.method'] = 'from_jql_query'
                if not issue_key:
                    all_defined = False
            elif type == 'confluence_page':
                issue_key = st.text_input(item_def["description"], key=pkey)
                item_def['src'] = issue_key
                item_def['TxtGetter.method'] = 'from_confluence_page'
                if not issue_key:
                    all_defined = False
            elif type == 'confluence_pages':
                issue_key = st.text_area(item_def["description"], key=pkey)
                item_def['src'] = issue_key
                item_def['TxtGetter.method'] = 'from_confluence_pages'
                if not issue_key:
                    all_defined = False
            elif type == 'free_form_text':
                user_input = st.text_area(item_def["description"], height=150, key=pkey)
                item_def['src'] = user_input
                item_def['TxtGetter.method'] = 'from_multiline_text'
                if not user_input:
                    all_defined = False
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
                else:
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
                        estimated_tokens = FlowUtils.estimate_tokens(text)
                        write_to_log(f"Estimated tokens {estimated_tokens}")

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
            pkey = self.format_internal_key(True, item_key, 'choice')

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
        
        for key, dep_path in depends_on.items():
            dep_step_name = self.step_name_from_path(dep_path)
            dep_step = self.app.get_step(dep_step_name)
            sub_key = self.subkey_from_path(dep_path, dep_step_name)
            dep_output_key = dep_step.get_output_key()
            if len(sub_key) > 0:
                token_map[key] = dep_output_key + '.' + sub_key
            else:
                token_map[key] = dep_output_key

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
            """ Run the loop - return true if a new interation occurs """
        
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

            # Assume no interacction
            interaction_occured = False
                
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
                    interaction_occured = True
                    response = LangChainUtils.chat_prompt_response(chat_model, initial_system_prompt, human_prompt, messages)

                # Show the response and add it to messages
                st.chat_message("assistant").markdown(response)

                # Update messages
                state_dict[messages_key].append({"role": "user", "content": human_prompt, "length" : human_prompt_length})
                state_dict[messages_key].append({"role": "assistant", "content": response})

            # Done
            return interaction_occured

        # Create output key
        output_key = self.get_output_key()

        # Internal state key
        messages_key = self.format_internal_key(True, 'messages')

        # Start
        if st.button("Generate"):
            state_dict[messages_key] = []

        # If started show chat dialogue
        if None != state_dict.get(messages_key):

            # Display chat dialogue      
            interaction_occured = do_chat_loop(
                state_dict=state_dict,
                chat_model=chat_model, 
                initial_system_prompt=initial_system_prompt, 
                initial_human_prompt=initial_human_prompt,
                messages_key=messages_key,
                hide_initial_prompt=hide_initial_prompt,
                retrieve_context=retrieve_context)
            
            # Rerun to update 
            if interaction_occured:
                st.rerun()

        # Done
        return 


