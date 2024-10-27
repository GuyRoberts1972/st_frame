""" Base class for flow apps """
import streamlit as st
from utils.get_text import TxtGetter as TxtGetter
from utils.step_utils import BaseFlowStep, StepConfigException
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
            subkey_path = dependency_path.removeprefix(dep_step_name).removeprefix('.')
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

        # Loop through steps saving
        state = self.get_state()
        for step_name, step in self.steps.items():
            step : BaseFlowStep = step
            if step.input_data_ready(state):
                step.show()

        # Save state
        self.state_manager.save_current_state()
