""" Base class for flow apps """
import streamlit as st
from utils.get_text import TxtGetter as TxtGetter
from utils.step_utils import BaseFlowStep, StepConfigException, StepStatus
from typing import Dict, Any


class BaseFlowApp:
    """ The bass flow app class """
    def __init__(self, config: Dict[str, Any], state_manager: Any):
        """ Initialise and display title etc """

        self._validate_config(config)
        
        # Init variables
        self.state_manager = state_manager
        self.config = config
        self.steps = {}

        # Title and description
        st.title(config['title'])
        st.write(config['description']) 

    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> None:
        required_keys = ['title', 'description', 'steps']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required key in config: {key}")
    
    def get_step_config(self, step_name):
        """ Get the step section of config """
        return self.config['steps'][step_name]
    
    def get_config(self):
        """ Get the config """
        return self.config
    
    def get_state(self):
        """ Get the state (pseudo) dict """
        return st.session_state
    
    def set_state(self, key, value):
        """ Set the key to the value """
        st.session_state[key] = value

    def clear_state(self, key):
        """ clear the key from state """
        st.session_state.pop(key, None)

    def get_step(self, step_name):
         """ Get the step by name """
         return self.steps[step_name]
    
    def get_prev_step(self, step_name):
        """ Get the step previous to the named one - or None """
        step_names = list(self.steps.keys())
        cur_index = step_names.index(step_name) 
        if cur_index == 0:
            return None
        prev_step_name = step_names[cur_index - 1]
        return self.steps[prev_step_name]
    
    def add_step(self, step : BaseFlowStep):
        """ Add a step, check its not a dupe and check 
        it's dependents steps are all ready present """
        
        # Check for duplicate
        step_name = step.get_name()
        if step_name in self.steps:
            raise StepConfigException(f"Problem loading step '{step_name}'. A step with that name already exists.")
        
        # Check input dependencies
        steps_config = self.config['steps']
        depends_on = step.get_depends_on()
        for dependency_name, dependency_path in depends_on.items():
            # Step is the first part of the dotted path
            dep_step_name = step.step_name_from_path(dependency_path)

            # Check the step exists
            if dep_step_name not in steps_config.keys():
                raise StepConfigException(f"Problem loading step '{step_name}'. Dependency step '{dep_step_name}' referenced by depedency '{dependency_name}' was not found")
        
            # If they key is a sub key on the step, check the step supports it
            subkey_path = step.subkey_from_path(dependency_path, dep_step_name)
            if len(subkey_path) > 0:
                dep_step = self.get_step(dep_step_name)
                dep_step_output_subkeys = dep_step.get_output_subkeys()
                if subkey_path not in dep_step_output_subkeys:
                    message =   f"Problem parsing '{step_name}'" \
                                f"dependency step '{dep_step_name}' does not support sub key '{subkey_path}'" \
                                f"in path {dependency_path} needed for '{dependency_name}'. " \
                                f"Supported keys are '{dep_step_output_subkeys}'"
                    raise StepConfigException(message)
        # Add
        self.steps[step_name] = step

    def load_steps(self):
        
        # Enum steps and add them
        for step_name, step_config in self.config['steps'].items():

            # Get class name
            if 'class' not in step_config:
                raise StepConfigException(f"Problem parsing step {step_name}. The class attribute is missing")
            step_class_name = step_config['class']

            # Add the step
            self.add_step(
                step = BaseFlowStep.create_instance(
                    class_name=step_class_name,
                    name=step_name,
                    app=self,
                )
            )
 
    def show_steps(self):
        """ Show the steps in the UI """

        from st_ui.step_list import StepContainer
        # Loop through steps
        step_container = StepContainer()
        flow_state = self.get_state()
            
        def render_step(step : BaseFlowStep, hide, expand, step_status, fn_step_content):
            """ Render the entire step including the container """
            
            def fn_step_content_wrapper():
                """ Render the step content and turn actions into buttons definitions """
                actions = fn_step_content()
                step_name = step.get_name()
                
                # Convert actions to buttons
                buttons = []
                for action in actions:
                    if action:
                        button = action.copy()
                        button['key'] = f"step_action_button_{step_name}_{action['text']}"
                        buttons.append(button)
                    else:
                        pass
                
                # Done
                return buttons

            # Visually show step state on header
            status_name = StepStatus.get_name(step_status)
            step_headng = f"{status_name} {step.heading}"
                        
            # Render the step in the container
            step_container.render_step(step_headng, fn_step_content_wrapper, expand, hide)

        # Show each of the steps
        for _, step in self.steps.items():
            step.show(flow_state, render_step)
                
        # Save state
        self.state_manager.save_session_to_state()