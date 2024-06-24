"""
This module contains all the prompt templates for the Architect agent.

Each prompt in this module is designed to guide the Architect agent in 
performing its tasks. The prompts cover a wide range of scenarios, from 
analyzing user input and creating comprehensive requirements documents, to 
breaking down projects into independent tasks and enforcing best practices in
microservice architecture, project folder structure, and clean-code development.

The prompts are used to instruct the Architect agent on how to respond to user 
inputs and how to structure its outputs. They are essential for ensuring that 
the Architect agent can effectively assist users in implementing their projects.
"""

from langchain_core.prompts import ChatPromptTemplate

from langchain.output_parsers import PydanticOutputParser

from pydantic import BaseModel

class ArchitectPrompts:
    """
    ArchitectPrompts class contains templates for guiding the Architect agent in its tasks.
    
    It includes templates for initial project requirements generation and for providing additional 
    information during project implementation. These templates ensure that the Architect agent can 
    effectively assist users in implementing their projects, adhering to best practices in 
    microservice architecture, project folder structure, and clean-code development.
    """

    INITIAL_TEMPLATE: str ="""
    As a Development Lead, you are entrusted with the implementation of the given project. 
    Conduct a thorough analysis of the user request and construct a comprehensive document 
    in markdown format necessary for project execution.
    
    You should also be proficient in decomposing them into autonomous tasks that can be 
    delegated to other team members.

    Mandate the utilization of microservice architecture, adhere to the best practice methods 
    for project folder structure, 12-factor application standards, domain-driven microservice 
    application design, clean-code development architecture standards, and code commenting 
    standards throughout the project.
    
    Enforce these user-requested standards as well:
    {user_requested_standards}

    The final project should encompass all the source files, configuration files, unit test files, 
    OpenAPI specification file for the project in YAML format, dependency package manager files, 
    Dockerfile, .dockerignore, and a .gitignore file.

    {format_instructions}

    User Request:
    {user_request}
    """

    ADDITIONAL_INFO_TEMPLATE: str = """
    As a Development Lead, you are responsible for implementing a given project. You have 
    previously prepared the requirements documents, tasks, and other necessary details for 
    your team members to complete the project.

    A team member has reached out to you requesting additional information to complete their 
    task. Please assist them.

    {format_instructions}

    Chat History:
    {chat_history}

    Previously Prepared Requirements Documents:
    {requirements_document}

    Current Task Team is Working On:
    {current_task}

    Question:
    {question}
    """

    def requirements_generation_prompt(self, pydantic_model: BaseModel) -> ChatPromptTemplate: 
        """
        This method generates a prompt for the initial project requirements based on the 
        provided Pydantic model.
        
        Args:
            pydantic_model (BaseModel): The Pydantic model containing the project requirements.

        Returns:
            ChatPromptTemplate: The generated prompt.
        """

        return ChatPromptTemplate.from_template(
            template=self.INITIAL_TEMPLATE,
            partial_variables = {
                "format_instructions": PydanticOutputParser(pydantic_object=pydantic_model)
            }
        )

    def additional_info_prompt(self, pydantic_model: BaseModel) -> ChatPromptTemplate:
        """
        This method generates a prompt for providing additional information during 
        project implementation based on the provided Pydantic model.
        
        Args:
            pydantic_model (BaseModel): The Pydantic model containing the additional information.

        Returns:
            ChatPromptTemplate: The generated prompt.
        """
                
        return ChatPromptTemplate.from_template(
            template=self.ADDITIONAL_INFO_TEMPLATE,
            partial_varibales = {
                "format_instructions": PydanticOutputParser(pydantic_object=pydantic_model)
            }
        )
