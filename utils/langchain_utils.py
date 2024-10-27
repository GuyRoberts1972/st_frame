""" Lang chain and LLM wrappers """
import boto3
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain_aws import ChatBedrock
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory

class LangChainUtils:
    ''' handles details about LLM models '''

    @staticmethod
    def get_chat_model_choices():
        
        # todo: move these to data
        choices = {
            "Claude 3 Sonnet - Standard (Default)" : {
                "description" : "Claude 3 Sonnet with standard settings",
                "model_id" : "anthropic.claude-3-sonnet-20240229-v1:0",
                "model_kwargs" : {"max_tokens": 10000, "temperature": 0.7}
            },
            "Claude 3 Haiku - Standard" : {
                "description" : "Claude 3 Haiku with standard settings",
                "model_id" : "anthropic.claude-3-haiku-20240307-v1:0",
                "model_kwargs" : {"max_tokens": 10000, "temperature": 0.7}
            },
            "Claude 3 Sonnet - Creative" : {
                "description" : "Claude 3 Sonnet with high temperature, prone to hallucinations",
                "model_id" : "anthropic.claude-3-sonnet-20240229-v1:0",
                "model_kwargs" : {"max_tokens": 10000, "temperature": 1.0}
            },
            "Claude 3 Sonnet - Accurate" : {
                "description" : "Claude 3 Sonnet with low temperature, not creative",
                "model_id" : "anthropic.claude-3-sonnet-20240229-v1:0",
                "model_kwargs" : {"max_tokens": 10000, "temperature": 0.1}
            },
            "Claude 3 Sonnet - Ten Tokens Max" : {
                "description" : "Claude 3 Sonnet with very short context window",
                "model_id" : "anthropic.claude-3-sonnet-20240229-v1:0",
                "model_kwargs" : {"max_tokens": 10, "temperature": 0.7}
            },
        }
    
        # Done
        return choices
    
    @staticmethod
    def get_chat_model(model_choice, region_name=None):
        ''' get the model to use for chat based on the choice '''
        
        # Get the values for the model choice
        chat_model_choices = LangChainUtils.get_chat_model_choices()
        if model_choice not in chat_model_choices:
            raise Exception(f"Invalid model choice '{model_choice}")
        
        model_choice = chat_model_choices[model_choice]

        # Set up the Bedrock client
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=region_name
        )

        # Initialize the ChatBedrock model
        chat = ChatBedrock(
            model_id=model_choice['model_id'],
            client=bedrock_runtime,
            model_kwargs=model_choice['model_kwargs'],
        )

        # Done
        return chat

    @staticmethod
    def list_available_models():
        ''' print a list of available models '''
       
        bedrock_client = boto3.client('bedrock')

        try:
            response = bedrock_client.list_foundation_models()
            
            print("Available models:")
            for model in response['modelSummaries']:
                print(f"Model ID: {model['modelId']}")
                print(f"Model Name: {model['modelName']}")
                print(f"Provider: {model['providerName']}")
                print("---")

        except Exception as e:
            print(f"An error occurred: {str(e)}")

    @staticmethod
    def simple_prompt_response(chat_model, initial_system_prompt, human_prompt):
        """ Simply prompt the model and get a response """
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=initial_system_prompt),
            ("human", human_prompt)
        ])
        chain = prompt | chat_model
        response = chain.invoke({"input": ""})
        return response.content

    @staticmethod
    def chat_prompt_response(chat_model, initial_system_prompt, human_prompt, prior_chat_history=None):
        prompt = ChatPromptTemplate.from_messages([
            ("system", initial_system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])

        # Initialize chat history
        chat_history = ChatMessageHistory()
        if prior_chat_history:
            for message in prior_chat_history:
                if message['role'] == 'user':
                    chat_history.add_user_message(message['content'])
                elif message['role'] == 'assistant':
                    chat_history.add_ai_message(message['content'])

        # Create a runnable chain
        chain = prompt | chat_model

        # Wrap the chain with message history
        chain_with_history = RunnableWithMessageHistory(
            chain,
            lambda session_id: chat_history,
            input_messages_key="input",
            history_messages_key="history"
        )

        # Run the chain
        response = chain_with_history.invoke(
            {"input": human_prompt},
            config={"configurable": {"session_id": "default"}}
        )

        # Done
        return response.content