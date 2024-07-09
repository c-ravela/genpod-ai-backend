"""
"""

from langchain_core.prompts import PromptTemplate

from langchain.output_parsers import PydanticOutputParser

from models.coder import CodeGeneration

class CoderPrompts:

    code_generation_prompt: PromptTemplate = PromptTemplate(
        template="""
        As a proficient programmer, you are part of a collaborative team effort to deliver a comprehensive 
        end-to-end project as requested by the user. Your expertise lies in crafting well-documented, optimized, 
        secure, and production-ready code.

        You are currently engaged in the following project:
        Project Name: '{project_name}'

        The project should be located at:
        Project Path: '{project_path}'

        The document provided below offers a detailed overview of the project, including critical facts and a set 
        of guidelines that must be strictly adhered to during the development process. These guidelines, carefully 
        designed and specified by your team lead, are intended to ensure the highest quality of work. It is imperative 
        that you diligently follow these guidelines:

        "{requirements_document}"

        Your strict adherence to these guidelines is vital for the successful and timely completion of the project. Let's 
        strive to uphold the standards set forth in the document and work collaboratively towards our shared objective.

        The project necessitates certain files and directories. The required folder structure for the project is as follows:
        "{folder_structure}"

        Please note, error messages will only be present if there is an issue with your previous response:
        "{error_message}"

        The instructions for formatting are as follows:
        {format_instructions}

        Now, here is your task to complete:
        {task}.
        """,
        input_variables=['project_name', 'project_path', 'requirements_document', 'folder_structure', 'error_message', 'task'],
        partial_variables={
            "format_instructions": PydanticOutputParser(pydantic_object=CodeGeneration).get_format_instructions()
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