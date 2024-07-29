"""
"""

from langchain_core.prompts import PromptTemplate

from langchain.output_parsers import PydanticOutputParser

from models.skeleton import FunctionSkeleton

class SkeletonGeneratorPrompts:

    skeleton_generation_prompt: PromptTemplate =PromptTemplate(
        template="""
    You are a highly skilled software developer assistant. Your task is to generate a detailed function skeleton based on the provided description.
    
    You are currently working on the following project:
    Project Name: '{project_name}'

    Project Path: '{project_path}'

    From document provided below you will find facts about the project and set of guidelines to be 
    followed while developing the project. Please adhere to the following guidelines specified by 
    your team lead:
    "{requirements_document}"

    The project requires certain files and directories. The required folder structure for the 
    project is as follows at path:
    "{folder_structure}"

    Error messages will only be present if there is an issue with your previous response. 
    "{error_message}"

    The instructions for formatting are as follows:
    {format_instructions}

    Please ensure that the function description is clear and detailed, specifying the exact steps or logic that need to be implemented within the function. 

    Format the files to be created as a list of strings. For example:
    "[file_path1, file_path2, file_path3, ..., file_pathN]"

    To complete each task, you should select at least one tool. The tools should be executed in 
    the order they are listed.

    Now, here is your task to complete.
    {task}.
    """,
            input_variables=['project_name', 'project_path', 'requirements_document', 'folder_structure', 'error_message', 'task' ],
            partial_variables= {
                "format_instructions": PydanticOutputParser(pydantic_object=FunctionSkeleton).get_format_instructions()
            }
        )
    
