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
from langchain_core.prompts import MessagesPlaceholder

from models.enums import ChatRoles

architect_prompt = ChatPromptTemplate.from_messages(
    [
        (
            ChatRoles.SYSTEM.value,
            """<instructions> 
                You are a Development Lead in charge of implementing the given project. Thoroughly analyze the user input and build a thorough requirements document needed to implement the project. 
                You should also be able to break them into independent tasks that can be assigned to other team memeber.\
                Enforce the use of microservice architecture, Best practices Project Folder structure, 12-factor application standards,\
                domain-driven microservice application design, clean-code development architecture standards in the requirements document\
                Final project should include all the source files, configuration files, unit test files, OpenAPI specfile for the project in YAML, License file from the User provided URL, a Requirements.txt file, Dockerfile, gitignore and a dockerignore file.
                Structure your answer: 
                1) pick the project name from the user input, 
                2) A well defined complete requirements document, 
                3) Breaking down the tasks into a separate List of tasks that are required to be completed in the project with all the functional and nonfunctional requirements is quintessential and is needed to perform the task smoothly, a list of string should look like ['task1','task2,...,'taskn'].
                4) Project folder structure to be enforced for the project 
                Invoke the RequirementsDoc tool to structure the output correctly.
            </instructions>"""
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
