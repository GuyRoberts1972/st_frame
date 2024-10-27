""" For use cases that provide analysis and summaries """
import streamlit as st
from utils.get_text import TxtGetter as TxtGetter
from utils.step_utils import BaseFlowStep, StepConfigException
from utils.app_utils import BaseFlowApp





class SummaryFlowApp(BaseFlowApp):
    """ Flow app class for summary flows """

    @staticmethod
    def run(config, state_manager):
        
        # Create app
        app = SummaryFlowApp(
            config=config,
            state_manager=state_manager
        )

        # Load it
        app.load_steps()

        # Display the steps
        app.show_steps()

        # Save the state
        app.state_manager.save_current_state()

        # Done
        return app
    
if __name__ == '__main__':
    
    # Example config
    config_yaml = """
    title: Example Summary App
    description: Demonstrate a Summary App
    steps:

        test_choose_llm:
            heading: Choose the LLM to test
            class: ChooseLLMFlavour
    
        test_define_input_defs:
            heading: Test inputs
            class: DefineInputDataStep
            depends_on:
            data_defs:
                other_text:
                    description: Paste relevant text Emails or Teams chats here
                    type: free_form_text
                jira_issues_list: 
                    description: Enter some jira issues
                    type: jira_issues

        retrieve_data:
            heading: Getting data
            class: RetrieveDataStep
            depends_on:
                data_sources: test_define_input_defs

        summary_options:
            heading: Choose summary options
            class: SelectPromptFragmentsStep
            fragment_options:
                summary_type:
                    label: Choose a test summary type
                    choices:
                        Short Summary: Provide a short and succinct summary
                        Long Essay: Pad it out with extra text and side stories
                language:
                    label: Choose a language
                    choices:
                        English: Use the queens english from aroud 1900
                        Jive: Use a language style associated with street Jive in black america
                        French: Use an assertive french style

        initial_system_prompt:
            heading: System prompt for chat loop
            class: FormatPromptStep
            depends_on:
                summary_type: summary_options.summary_type
                language: summary_options.language
            template: |
                You are an assistant that is good at summarising text.
                You will be given some text to summarise. 
                Use the guidance below to do that:
                {summary_type} 
                {language}
                Then work with the human to refine to a final draft
        
        initial_human_prompt:
            heading: Human prompt for chat loop
            class: FormatPromptStep
            depends_on:
                other_text: retrieve_data.other_text
                jira_issues_list: retrieve_data.jira_issues_list
            template: |
                Please summarise the below text 
                ---- START: FREE FORM TEXT ----
                {other_text}
                ---- END: FREE FORM TEXT ----
                ---- START: TEXT FROM JIRA ISSUES ----
                {jira_issues_list}
                ---- END: TEXT FROM JIRA ISSUES ----

        refinement_loop:
            heading: Review and Refine Draft
            class: ChatLoopStep
            depends_on:
                initial_system_prompt: initial_system_prompt
                initial_human_prompt: initial_human_prompt
                chat_model_choice: test_choose_llm

    """

    # Parse the YAML string into a Python dictionary
    import yaml
    config = yaml.safe_load(config_yaml)

    # Stub class for saving
    class StubStatemanager:
        def save_current_state(self):
            pass

    # Run the example app
    SummaryFlowApp.run(config, StubStatemanager())
