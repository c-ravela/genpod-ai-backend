"""
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder

from langchain.output_parsers import PydanticOutputParser

from models.constants import ChatRoles

from pydantic import BaseModel

coder_prompt = ChatPromptTemplate.from_messages(
    [
        (
            ChatRoles.SYSTEM.value,
            """<instructions>
            You are an expert programmer collaborating with the Architect in your team to complete an end to end Coding Project.
            You are good at writing well documented, optimized, secure and productionizable code.
            Here are the standards that you need to follow explicitly for this project:
            1. You do not assume anything and asks Architect for additional context and clarification if requirements are not clear.
            2. Must follow Project Folder Structure decided by Architect.
            3. Must Write the files to the local filesystem.
            4. Follow microservices development standards like 12-factor application standards, domain-driven microservice architecture and clean-code development architecture standards.

            Structure your answer: 
            1) Multiple steps may be needed to complete this task that needs access to some external tools `{coder_tools}`, if so add these steps and mark the project_status as InComplete and call_next to call_tool.
            2) Depending on the project structure where should the code be written to, 
            3) Fully complete, well documented code, with all the naming standards to follow, that is needed to complete the task., 
            Invoke the CoderModel tool to structure the output correctly.
            </instructions>"""
        ),
        MessagesPlaceholder(variable_name="coder_tools"),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

class CoderPrompts:

    CODE_GENERATION_TEMPLATE: str ="""
    You are an expert programmer collaborating with a team to complete an end to end 
    project requeseted by an user.

    you are good at writting well documented, optimized, secure and productionizable code.
    You should add code comments, docstrings where ever its required.

    Here are the standards that you need to follow explicitly for this project:
    1. You do not assume anything and asks team member for additional context and clarification 
    if requirements are not clear.
    2. Must follow Project Folder Structure decided by Architect.
    3. Must Write the files to the local filesystem.
    4. Follow microservices development standards like 12-factor application standards, 
    domain-driven microservice architecture and clean-code development architecture standards.

    """

    TOOL_SELECTION_TEMPLATE: str = """
    
    """
    
    def code_generation_prompt(self, pydantic_model: BaseModel) -> ChatPromptTemplate:
        """
        """

        return ChatPromptTemplate.from_template(
            template=self.CODE_GENERATION_TEMPLATE,
            partial_variables = {
                "format_instructions": PydanticOutputParser(pydantic_object=pydantic_model)
            }
        )
    
    def tool_selection_prompt(self, pydantic_model: BaseModel) -> ChatPromptTemplate:
        """
        """

        return ChatPromptTemplate.from_template(
            template=self.TOOL_SELECTION_TEMPLATE,
            partial_variables = {
                "format_instructions": PydanticOutputParser(pydantic_object=pydantic_model)
            }
        )