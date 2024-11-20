""" Class hierarchy for flow steps """
import streamlit as st
from enum import IntEnum, Enum, auto
from abc import ABC, abstractmethod
from typing import Dict, Any
import time
import re
from utils.langchain_utils import LangChainUtils
from utils.get_text import TxtGetter as TxtGetter
from utils.flow_utils import FlowUtils

class StepConfigException(Exception):
    """ exception class for parsing errors """
    pass


# Forward def for type hint
class BaseFlowApp:
    pass

class BaseFlowStep_ack_mgmb(ABC):
    """ Abstract class to manaage acknowleggment status
    i.e. buttons like confirm and start that have a state
    """

    @abstractmethod
    def format_internal_key(**kwargs):
        """ Abstract method implemented by implementation """
        pass

    @abstractmethod
    def get_option(**kwargs):
        """ Abstract method implemented by implementation """
        pass

    def _validate_ack(self, ack):
        """ check its a valid acknowledgement type """
        if not ack in ['changes', 'start']:
            raise Exception(f"bad acknowledgment type '{ack}'")

    def get_ack_key(self, ack):
            """ Return False if acknowlegement is required but has not yet been recieved """
            self._validate_ack(ack)
            ack_key = self.format_internal_key(True, ack, 'acknowledgement')
            return ack_key

    def get_ack_status_description_text(self, ack):
        """ Get the descripton text to display for the ack,
        either from the part after the '|' in the option value or
        by using a default string with the button name
        """
        self._validate_ack(ack)
        opt_ack_value = self.get_option(f"ack_{ack}", ack)
        parts = opt_ack_value.split('|')
        if len(parts) > 1:
            return parts[1]
        return f"Click {parts[0]} to proceed."

    def get_ack_button_text(self, ack):
        """ Get the button text """
        self._validate_ack(ack)
        opt_ack_value = self.get_option(f"ack_{ack}", ack)
        parts = opt_ack_value.split('|')
        return parts[0]

    def get_ack_button(self, ack):
        """ Return a dict that represents a button"""
        self._validate_ack(ack)
        action = {
            "text" : self.get_ack_button_text(ack),
            "on_click" : lambda : self.on_ack(ack)
        }

        return action

    def check_ack(self, ack):
        """ Return False if acknowlegement is required but has not yet been recieved """
        self._validate_ack(ack)
        opt_ack_value = self.get_option(f"ack_{ack}", None)
        if not opt_ack_value:
            return True
        ack_key = self.get_ack_key(ack)
        if True == st.session_state.get(ack_key):
            return True
        return False

    def on_ack(self, ack):
        """ Set acknowledged in state """
        self._validate_ack(ack)
        ack_key = self.get_ack_key(ack)
        st.session_state[ack_key] = True

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


class StepStatus(IntEnum):
    """ Enum to represent the status of a step """
    WAITING = auto()
    ENQUEUED = auto()
    ACTIVE_ACK_START = auto()
    ACTIVE = auto()
    ACTIVE_ACK_CHANGES = auto()
    DONE = auto()

    def get_name(self):
        """Returns a human-readable name for the status."""
        names = {
            self.WAITING: "WAITING",
            self.ENQUEUED: "ENQUEUED",
            self.ACTIVE_ACK_START: "STARTING",
            self.ACTIVE: "ACTIVE",
            self.ACTIVE_ACK_CHANGES: "CONFIRM",
            self.DONE: "DONE"
        }
        return names.get(self, "Unknown")

    def get_description(self):
        """Returns a description of the status."""
        descriptions = {
            self.WAITING: "Step can't start since it's dependent on upstream outputs",
            self.ENQUEUED: "Not started yet as the previous step is not done",
            self.ACTIVE_ACK_START: "The step is active but is configured to prompt the user to acknowledge the start",
            self.ACTIVE: "The step is active, working or prompting for input",
            self.ACTIVE_ACK_CHANGES: "The step is done but is configured and waiting for user to acknowledge changes",
            self.DONE: "The step is done and next step can start"
        }
        return descriptions.get(self, "No description available")

    def get_icon(status):
        """ Maps a StepStatus Unicode icon."""
        icon_map = {
            StepStatus.WAITING: "⏳",
            StepStatus.ENQUEUED: "⭕",
            StepStatus.ACTIVE_ACK_START: "🔔",
            StepStatus.ACTIVE: "▶️",
            StepStatus.ACTIVE_ACK_CHANGES: "✋",
            StepStatus.DONE: "✅",
        }

        return icon_map.get(status, "❓")

class StatusCriteria(Enum):
    """ Enum for all the options criteria that can be matched against a status """
    afterActive = 'afterActive'
    waitingEnqueuedAndAckOnly = 'waitingEnqueuedAndAckOnly'
    anyActive = 'anyActive'
    always = 'always'
    never = 'never'
    waitingOnly = 'waitingOnly'
    enqueuedOnly = 'enqueuedOnly'
    activeAckStartOnly = 'activeAckStartOnly'
    activeOnly = 'activeOnly'
    activeAckChangesOnly = 'activeAckChangesOnly'
    doneOnly = 'doneOnly'

    @staticmethod
    def status_matches_criteria(opt_criteria: str, step_status: StepStatus) -> bool:
        """ returns true if the status matches the criteria """
        try:
            enum_criteria = StatusCriteria(opt_criteria)
        except ValueError:
            valid_options = ", ".join([criteria.value for criteria in StatusCriteria])
            raise StepConfigException(f"Unknown option '{opt_criteria}'. Valid options are: {valid_options}")

        criteria_map = {
            StatusCriteria.afterActive: {StepStatus.ACTIVE_ACK_START, StepStatus.ACTIVE, StepStatus.ACTIVE_ACK_CHANGES, StepStatus.DONE},
            StatusCriteria.anyActive: {StepStatus.ACTIVE_ACK_START, StepStatus.ACTIVE, StepStatus.ACTIVE_ACK_CHANGES},
            StatusCriteria.waitingEnqueuedAndAckOnly: {StepStatus.WAITING, StepStatus.ENQUEUED, StepStatus.ACTIVE_ACK_CHANGES, StepStatus.ACTIVE_ACK_START},
            StatusCriteria.always: set(StepStatus),
            StatusCriteria.never: set(),
            StatusCriteria.waitingOnly: {StepStatus.WAITING},
            StatusCriteria.enqueuedOnly: {StepStatus.ENQUEUED},
            StatusCriteria.activeAckStartOnly: {StepStatus.ACTIVE_ACK_START},
            StatusCriteria.activeOnly: {StepStatus.ACTIVE},
            StatusCriteria.activeAckChangesOnly: {StepStatus.ACTIVE_ACK_CHANGES},
            StatusCriteria.doneOnly: {StepStatus.DONE}
        }

        return step_status in criteria_map[enum_criteria]

class BaseFlowStep(BaseFlowStep_key_mgmt, BaseFlowStep_ack_mgmb):
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

    def get_option(self, option_name, default=None):
        """ Get a step option, precedence order if step level config, then flow config """

        step_config = self.get_step_config()
        flow_config = self.get_app().get_config()

        # Get a option, precedence order if step level config, then flow config
        option_value = FlowUtils.nested_get(flow_config, f"step_options.{option_name}", default)
        option_value = FlowUtils.nested_get(step_config, f"step_options.{option_name}", option_value)
        return option_value

    def show(self, flow_state, render_step):
        """ Asses status and show the step """

        # Short cuts
        step_config = self.get_step_config()
        step_state = self.get_app().get_state()

        def get_step_status():
            """ Get the current status of the step """

            # Waiting for data from dependency steps
            if not self.input_data_ready(flow_state):
                return StepStatus.WAITING
            # Waiting for previous step to be done
            elif not self.prev_step_is_done(flow_state):
                return StepStatus.ENQUEUED
            # If our data is not ready we are active
            elif not self.output_data_ready(flow_state):
                if not self.check_ack('start'):
                    return StepStatus.ACTIVE_ACK_START
                return StepStatus.ACTIVE
            elif not self.check_ack('changes'):
                return StepStatus.ACTIVE_ACK_CHANGES
            else:
                return StepStatus.DONE

        # Get status now
        step_status = get_step_status()

        # Determine visibility
        opt_visibility = self.get_option('visibility', StatusCriteria.always)
        visible = StatusCriteria.status_matches_criteria(opt_visibility, step_status)

        # Determine expandability
        opt_expandability = self.get_option('expandability', StatusCriteria.anyActive)
        expand = StatusCriteria.status_matches_criteria(opt_expandability, step_status)

        # Status description visible
        opt_status_description_visibility = self.get_option('status_description_visibility', StatusCriteria.waitingEnqueuedAndAckOnly)
        status_description_visible = StatusCriteria.status_matches_criteria(opt_status_description_visibility, step_status)

        def format_status_description():
            """ Format a string that describes the steps status """

            dependency_step_headings = self.get_dependency_step_headings()
            prev_step_heading = self.get_prev_step_heading()
            status_description = f"This step is '{step_status}'"
            if step_status == StepStatus.WAITING:
                status_description = f"This step is waiting for data from the following steps '{dependency_step_headings}'"
            elif step_status == StepStatus.ENQUEUED:
                status_description = f"This step is waiting for the previous step '{prev_step_heading}' to be done."
            elif step_status == StepStatus.ACTIVE_ACK_START:
                status_description = self.get_ack_status_description_text('start')
            elif step_status == StepStatus.ACTIVE_ACK_CHANGES:
                status_description = self.get_ack_status_description_text('changes')

            # Done
            return status_description

        def get_button(button, func):
            """ Get a tuple that represents a button if configured or None
            (button text, on click handler)
            """
            opt_button = self.get_option(f"btn_{button}", None)
            if not opt_button:
                return None
            parts = opt_button.split('|')
            text = parts[0]
            help_text = parts[1] if len(parts)>1  else None
            action = {
                "text" : text,
                "help_text" : help_text,
                "on_click" : func
                }
            return action

        # Action buttons
        act_reset = get_button('reset', lambda : self.on_reset())
        act_reset_to_prev = get_button('reset_to_prev', lambda : self.on_reset_to_prev_step())
        act_reset_from_here = get_button('reset_from_here', lambda : self.on_reset_from_here())
        act_reset_all = get_button('reset_all', lambda : self.on_reset_all())
        act_view_JSON = get_button('view_json', lambda : self.on_view_JSON())

        def fn_step_content():
            ''' Render the contents of the step, return available actions'''

            # Status Descrition
            if status_description_visible:
                st.write(format_status_description())

            if step_status == StepStatus.WAITING:
                # Actions
                actions = []
            elif step_status == StepStatus.ENQUEUED:
                # Actions
                actions = []
            elif step_status == StepStatus.ACTIVE_ACK_START:
                # Actions
                act_ack_start = self.get_ack_button('start')
                actions = [act_ack_start]
            elif step_status == StepStatus.ACTIVE:
                # Do it
                self.do(step_config, step_state, step_status)
                # Actions
                actions = [act_reset, act_reset_to_prev, act_reset_all]
                actions = actions + [act_view_JSON]
            elif step_status == StepStatus.ACTIVE_ACK_CHANGES:
                # Do it
                self.do(step_config, step_state, step_status)
                # Actions
                act_ack_changes = self.get_ack_button('changes')
                actions = [act_ack_changes]
            elif step_status == StepStatus.DONE:
                # Do it
                self.do(step_config, step_state, step_status)
                # Actions
                actions = [act_reset, act_reset_to_prev, act_reset_from_here, act_reset_all]
                actions = actions + [act_view_JSON]
            else:
                st.warning('This step is an unknown state')

            # Return the available actions
            return actions

        # Render
        render_step(
            step=self,
            hide=not visible,
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
        """ Clear this step's state """


        # Clear the output key
        if reset_output_key:
            output_key = self.get_output_key()
            st.session_state[output_key] = None

        # Clear the internal keys
        if reset_internal_keys:
            internal_keys = self.get_internal_keys(include_pdata=True, include_vdata=True)
            for internal_key in internal_keys:
                st.session_state[internal_key] = None

    def on_reset_all(self, reset_output_key=True, reset_internal_keys=True):
        """ Clear the state of all the steps in the flow """

        app = self.get_app()
        step_names = app.get_step_names()
        for step_name in step_names:
            step = app.get_step(step_name)
            step.on_reset(reset_output_key, reset_internal_keys)

    def on_reset_from_here(self, reset_output_key=True, reset_internal_keys=True):
        """ Clear this step's state and all the subsequent steps in the flow """

        cur_step = self
        while cur_step != None:
            cur_step.on_reset(reset_output_key, reset_internal_keys)
            cur_step = cur_step.get_next_step()

    def on_reset_to_prev_step(self, reset_output_key=True, reset_internal_keys=True):
        """ Clear this step's state and the previous ones """

        self.on_reset(reset_output_key, reset_internal_keys)
        self.get_prev_step().on_reset(reset_output_key, reset_internal_keys)

    def on_view_JSON(self):
        """ View this steps json """

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
        ''' Get the previous step or None '''
        return self.get_app().get_prev_step(self.get_name())

    def get_next_step(self):
        ''' Get the next step or None '''
        return self.get_app().get_next_step(self.get_name())

    def get_prev_step_heading(self, default='No Previous Step'):
        """ Get the heading of the previous step - or return default"""
        prev_step = self.get_prev_step()
        if None == prev_step:
            return default
        return prev_step.get_heading()

    def prev_step_is_done(self, flow_state):
        ''' Return true if the previous steps is done - returns True if this is the first step
        A step is done if output is ready and any confirmation ack is recieved
        '''
        prev_step = self.get_prev_step()
        if None == prev_step:
            return True
        if not prev_step.output_data_ready(flow_state):
            return False
        return prev_step.check_ack('changes')

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


    def do(self, step_config, state_dict, step_status):
        """ Show the LLM flavours and allow the user to select """

        # Disable widgets if done
        disabled = (step_status == StepStatus.DONE)

        text = 'Choose the chat model'
        pkey = self.format_internal_key(True, 'model_select')
        chat_model_choices_list = list(LangChainUtils.get_chat_model_choices().keys())

        # Handle None pkey - default to first choice
        if None == state_dict.get(pkey):
            state_dict[pkey] = chat_model_choices_list[0]

        # Show selector
        chat_model_choice = st.selectbox(text, chat_model_choices_list, key=pkey, disabled=disabled)

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

    def do(self, step_config, state_dict, step_status):
        """ Create the widgets """

        # Get data defs
        if 'data_defs' not in step_config:
            raise StepConfigException(f"Problem parsing step {self.get_name()}. The 'data_defs' attribute is missing")
        data_defs = step_config['data_defs']

        # Show one input at a time
        show_all_at_once = step_config.get('show_all_at_once', True)

        # Disable widgets if done
        disabled = (step_status == StepStatus.DONE)

        # Loop through input items
        all_defined = True
        for item_key, item_def in data_defs.items():

            # Don't show anymore last one was not defined
            if not show_all_at_once and not all_defined:
                break

            # Get type
            input_type  = item_def['type']

            # Per item internal state keys
            pkey = self.format_internal_key(True, item_key, input_type, 'src')
            vkey = self.format_internal_key(False, item_key, input_type, 'src')

            # Default value if present
            default_value = item_def.get('default_value')

            # Types of input supported by create_input_widget
            INPUT_TYPES = {
                'url': ('text_input', 'from_url'),
                'urls': ('text_area', 'from_urls'),
                'jira_issue': ('text_input', 'from_jira_issue'),
                'jira_issues': ('text_input', 'from_jira_issues'),
                'jira_jql_query': ('text_input', 'from_jql_query'),
                'confluence_page': ('text_input', 'from_confluence_page'),
                'confluence_pages': ('text_area', 'from_confluence_pages'),
                'free_form_text': ('text_area', 'from_multiline_text'),
            }

            def create_input_type(input_type: str, item_def: Dict[str, Any], pkey: str, default_value: Any, disabled: bool) -> Any:
                """ Handle common text_input and text_area input types """
                widget_type, getter_method = INPUT_TYPES.get(input_type, (None, None))
                if widget_type is None:
                    raise StepConfigException(f"Unknown input type '{input_type}'")

                # Set the default value. Using the 'value' param for text_areas seems unreliable
                if None == state_dict.get(pkey):
                        state_dict[pkey] = default_value

                if widget_type == 'text_input':
                    widget = st.text_input(item_def["description"], key=pkey, disabled=disabled)
                elif widget_type == 'text_area':
                    widget = st.text_area(item_def["description"], key=pkey, disabled=disabled)
                else:
                    raise StepConfigException(f"Unsupported widget type '{widget_type}'")

                item_def['src'] = widget
                item_def['TxtGetter.method'] = getter_method
                return widget

            # Switch on type
            if input_type in INPUT_TYPES:
                widget = create_input_type(input_type, item_def, pkey, default_value, disabled)
                if not widget:
                    all_defined = False
            elif input_type == 'uploaded_files':
                # Handle file upload differently
                file_types = ['pdf', 'docx', 'pptx', 'txt', 'xls', 'xlsx', 'csv']
                if None == state_dict.get(vkey):
                    temp_unique_key = vkey + str(int(time.time() * 1000000))
                    state_dict[vkey] = temp_unique_key
                else:
                    temp_unique_key = state_dict[vkey]

                uploaded_files = st.file_uploader("Choose files", type=file_types, accept_multiple_files=True, key=temp_unique_key, disabled=disabled)
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
                raise StepConfigException(f"Problem parsing step '{self.get_name()}'. Unknown input type '{input_type}'")

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
            'heading' : 'Retrieve  data',
            'step_options' : {
                  'ack_start' : 'Start|Click start to retrieve the data'
            }
        }

        # Parent
        super().__init__(
            name=name,
            app=app,
            defaults=defaults
        )

        # Our internal log key
        self.internal_log_key = f'{self.pdata_prefix}{self.name}_retrieved_data_log'


    def do(self, step_config, state_dict, step_status):
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

        output_key = self.get_output_key()
        if None == state_dict.get(output_key):
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

        # Write the log data if present
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

    def do(self, step_config, state_dict, step_status):
        """ Create the widgets """
        # Disable widgets if done
        disabled = (step_status == StepStatus.DONE)

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
            choice = st.selectbox(label, choices_list, key=pkey, disabled=disabled)
            state_dict[output_key][item_key] = choices[choice]

    def get_output_subkeys(self):
        """ Return sub keys that will be in the output dict """
        return self.step_config['fragment_options'].keys()


class FormatPromptStep(BaseFlowStep):
    """ Format a prompt template """

    def __init__(self, name, app):

        # Defaults for this step type
        defaults = {
            'heading' : 'Format prompt template',
            'step_options' : {
                'ack_changes' : None,
                'ack_start' : None,
            }
        }

        # Parent
        super().__init__(
            name=name,
            app=app,
            defaults=defaults
        )

    def do(self, step_config, state_dict, step_status):
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

    def do(self, step_config, state_dict, step_status):
        """ Setup and run the chat loop"""

        # Get dependency
        initial_system_prompt = state_dict[self.get_dependency_key('initial_system_prompt')]
        initial_human_prompt = state_dict[self.get_dependency_key('initial_human_prompt')]
        chat_model_choice = state_dict[self.get_dependency_key('chat_model_choice')]
        chat_model = LangChainUtils.get_chat_model(chat_model_choice)

        # Get options
        retrieve_context = step_config.get("retrieve_context", True)
        hide_initial_prompt = step_config.get("hide_initial_prompt", True)
        input_place_holder_text = step_config.get("input_place_holder_text", "Type a question.")


        def write_chat_message(role, message):
            """ Write a chat message for the role """

            # Escape dollar signs to avoid LaTeX type setting
            message = re.sub(r'(?<!\$)\$(?!\$)', '&#36;', message)
            st.chat_message(role).markdown(message)


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
                    write_chat_message(message["role"], content)

            # Get the human prompt
            human_prompt = st.chat_input(placeholder=input_place_holder_text)

            # First time through use the initial prompt
            if len(messages) == 0 and initial_human_prompt != None:
                human_prompt = initial_human_prompt

            # Assume no interacction
            interaction_occured = False

            # Submit to the model
            if human_prompt:
                # Display the prompt - if it's not the first
                if not hide_initial_prompt:
                    write_chat_message("user", human_prompt)

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
                write_chat_message("assistant", response)

                # Update messages
                state_dict[messages_key].append({"role": "user", "content": human_prompt, "length" : human_prompt_length})
                state_dict[messages_key].append({"role": "assistant", "content": response})

            # Done
            return interaction_occured

        # Create output key
        output_key = self.get_output_key()

        # Internal state key
        messages_key = self.format_internal_key(True, 'messages')

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


