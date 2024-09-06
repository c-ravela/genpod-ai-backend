"""
"""
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from models.coder_models import CodeGenerationPlan


class CoderPrompts:

    code_generation_prompt: PromptTemplate = PromptTemplate(
        template="""
        As a skilled programmer, you are an integral part of a team effort to deliver a comprehensive end-to-end 
        project as per the user's request. Your expertise is in developing well-documented, optimized, secure, and 
        production-ready code. Please focus solely on the assigned task.

        Follow the function skeleton to generate the code in the specific files.

        You will also be provided the unit test cases the functions that you are going to create should pass when completed

        You are currently working on the following project:
        Project Name: '{project_name}'

        The project should be located at:
        Project Path: '{project_path}'

        Below is a detailed overview of the project, including essential information and a set of guidelines that must 
        be strictly followed during the development process. These guidelines, meticulously designed and specified by 
        your team lead, aim to ensure the highest quality of work. It is crucial that you diligently adhere to these guidelines:

        "{requirements_document}"

        Your strict compliance with these guidelines is essential for the successful and timely completion of the project. Let's 
        strive to maintain the standards set forth in the document and work collaboratively towards our common goal.

        The project requires certain files and directories. The required folder structure for the project is as follows:
        "{folder_structure}"

        Please adhere strictly to the restrictions for command execution. Do not use pipe or any command combining symbols. 
        If needed, pass them as separate commands. Only choose those that are necessary for task completion.

        Please note, error messages will only appear if there is an issue with your previous response:
        "{error_message}"

        Please refrain from responding with anything outside of the task's scope.

        The instructions for formatting are as follows:
        {format_instructions}

        Now, here is your task to complete:
        {task}.

        These are the function skeletons for which you have to write the code to complete the functionality if the given task requires the function generation or it will be "No_skeleton".
        {functions_skeleton}.

        These are the unit test cases the functions you create should pass when executed if the given task requires the function generation or it will be "No UnitTests".:
        {unit_test}

        """,
        input_variables=['project_name', 'project_path', 'requirements_document', 'folder_structure', 'error_message', 'task','functions_skeleton','unit_test'],
        partial_variables={
            "format_instructions": PydanticOutputParser(pydantic_object=CodeGenerationPlan).get_format_instructions()
        }


    )
    
    # def code_generation_prompt(self) -> PromptTemplate:
    #     """
    #     """

    #     return PromptTemplate(
    #         template=self.CODE_GENERATION_TEMPLATE,
    #         input_variables=[
    #             "project_name", "requirements_document", "project_path", 
    #             "folder_structure", "additional_information", "error_message",
    #             "tools", "task"
    #         ],
    #         partial_variables= {
    #             "format_instructions": PydanticOutputParser(pydantic_object=CoderModel).get_format_instructions()
    #         }
    #     )
    
    # def tool_selection_prompt(self, pydantic_model: BaseModel) -> ChatPromptTemplate:
    #     """
    #     """

    #     return ChatPromptTemplate.from_template(
    #         template=self.TOOL_SELECTION_TEMPLATE,
    #         partial_variables = {
    #             "format_instructions": PydanticOutputParser(pydantic_object=pydantic_model)
    #         }
    #     )