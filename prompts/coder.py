"""
"""

from langchain_core.prompts import PromptTemplate

from langchain.output_parsers import PydanticOutputParser

from models.coder import CoderModel

class CoderPrompts:

    CODE_GENERATION_TEMPLATE: str ="""
    As an expert programmer, you are collaborating with a team to complete an end-to-end project 
    requested by a user. Your strengths lie in writing well-documented, optimized, secure, and 
    production-ready code. 

    Project Name: '{project_name}'

    Project Path: '{project_path}'

    From document provided below you will find facts about the project and set of guidelines to be 
    followed while developing the project. Please adhere to the following guidelines specified by 
    your team lead:
    "{requirements_document}"

    The project requires certain files and directories. The required folder structure for the 
    project is as follows at path:
    "{folder_structure}"

    If you need clarification on any aspect of the task, do not make assumptions. Instead, 
    conclude that additional information is needed. Generate the output accordingly, and the 
    required information will be provided to you. Additional information is only available 
    upon request:
    "{additional_information}"

    If the provided additional information is insufficient and you are unable to complete the 
    task, you may conclude that the task cannot be finished.

    Error messages will only be present if there is an issue with your previous response. 
    "{error_message}"

    The instructions for formatting are as follows:
    {format_instructions}

    Format the files to be created as a list of strings. For example:
    "[file_path1, file_path2, file_path3, ..., file_pathN]"

    You have access to the following tools:
    {tools}.

    To complete each task, you should select at least one tool. The tools should be executed in 
    the order they are listed.

    Now, here is your task to complete.
    {task}.
    """
    
    def code_generation_prompt(self) -> PromptTemplate:
        """
        """

        return PromptTemplate(
            template=self.CODE_GENERATION_TEMPLATE,
            input_variables=[
                "project_name", "requirements_document", "project_path", 
                "folder_structure", "additional_information", "error_message",
                "tools", "task"
            ],
            partial_variables= {
                "format_instructions": PydanticOutputParser(pydantic_object=CoderModel).get_format_instructions()
            }
        )
    
    # def tool_selection_prompt(self, pydantic_model: BaseModel) -> ChatPromptTemplate:
    #     """
    #     """

    #     return ChatPromptTemplate.from_template(
    #         template=self.TOOL_SELECTION_TEMPLATE,
    #         partial_variables = {
    #             "format_instructions": PydanticOutputParser(pydantic_object=pydantic_model)
    #         }
    #     )