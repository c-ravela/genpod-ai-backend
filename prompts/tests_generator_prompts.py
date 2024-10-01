"""
"""

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from models.tests_generator_models import FunctionSkeleton, TestCodeGeneration, FileFunctionSignatures


class TestGeneratorPrompts:

    test_generation_prompt: PromptTemplate =PromptTemplate(
        template="""
        As an expert programmer specialized in Unit test case generation, generate unit test case for the tasks that have functionality which requires unit test cases. In a test driven development you play a crucial role in creating the unit test cases first using which user will create their functionality to abide by the test cases. You are collaborating with a team to complete an end-to-end project 
        requested by a user. You should generate the unit test cases using the functions skeletons that are provided 

        You are currently working on the following project:
        Project Name: '{project_name}'

        Project Path: '{project_path}'

        Below is a detailed overview of the project, including essential information and a set of guidelines that must 
        be strictly followed during the development process. These guidelines, meticulously designed and specified by 
        your team lead, aim to ensure the highest quality of work. It is crucial that you diligently adhere to these guidelines:
        "{requirements_document}"

        The function skeletons in a given file 

        Error messages will only be present if there is an issue with your previous response. 
        "{error_message}"

        The instructions for formatting are as follows:
        {format_instructions}

        Format the files to be created as a list of strings. For example:
        "[file_path1, file_path2, file_path3, ..., file_pathN]"

        To complete each task, you should select at least one tool. The tools should be executed in 
        the order they are listed.

        Now, here is your task to complete.
        {task}.

        These are the functions skeletons dictionary the key contains the path where the functions are supposed to be created and value contains the function skeleton with function name, input parameters, return type and function description for which you need to create unit test cases 
        "{functions_skeleton}"
        """,
        input_variables=['project_name', 'project_path', 'requirements_document', 'error_message', 'task' , 'functions_skeleton'],
        partial_variables= {
            "format_instructions": PydanticOutputParser(pydantic_object=TestCodeGeneration).get_format_instructions()
        }
    )
    
    skeleton_generation_prompt: PromptTemplate = PromptTemplate(
        template="""
        You are a highly skilled software developer assistant. Your task is to generate a detailed function skeleton based on the provided description.


        You are currently working on the following project:
        Project Name: '{project_name}'

        Project Path: '{project_path}'

        Below is a detailed overview of the project, including essential information and a set of guidelines that must 
        be strictly followed during the development process. These guidelines, meticulously designed and specified by 
        your team lead, aim to ensure the highest quality of work. It is crucial that you diligently adhere to these guidelines:
        "{requirements_document}"

        Error messages will only be present if there is an issue with your previous response. 
        "{error_message}"

        The instructions for formatting are as follows:
        {format_instructions}

        Please ensure that the function description is clear and detailed, specifying the exact steps or logic that need to be implemented within the function. 

        Format the files to be created as a list of strings. For example:
        "[file_path1, file_path2, file_path3, ..., file_pathN]"

        Now, here is your task to complete.
        {task}.
        """,
        input_variables=['project_name', 'project_path', 'requirements_document', 'error_message', 'task' ],
        partial_variables= {
            "format_instructions": PydanticOutputParser(pydantic_object=FunctionSkeleton).get_format_instructions()
        }
    )

    skeleton_generation_for_issue_prompt: PromptTemplate = PromptTemplate(
        template="""
        You are a skilled software developer tasked with generating a detailed function signature based on the provided description. 

        Your task involves reviewing the current business logic of the file and the related issue. If necessary, you should update the function signature accordingly. 

        Here are the specific details you need to consider:
        
        **Current Business Logic:**
        ```
        {file_content}
        ```

        **Issue Details:**
        ```
        {issue_details}
        ```

        **Project Information:**
        - **Project Name:** `{project_name}`
        - **Project Path:** `{project_path}`

        **Project Overview and Guidelines:**
        Below is a comprehensive overview of the project, including essential information and guidelines that must be strictly adhered to during the development process. These guidelines have been meticulously crafted by your team lead to ensure the highest quality of work:
        ```
        {requirements_document}
        ```

        **Error Handling:**
        Please note that error messages will be provided only if there are issues with your previous response:
        ```
        {error_message}
        ```

        **Formatting Instructions:**
        Ensure to follow these formatting instructions when defining the function signature:
        ```
        {format_instructions}
        ```

        **Instructions:**
        - Clearly describe the function, including its purpose, parameters, return types, and any specific logic that needs to be implemented.
        - Provide step-by-step guidance on how the function should operate to resolve the given issue effectively.
        - Use proper formatting and follow the guidelines outlined above to ensure clarity and correctness.

        Please complete the task by generating the function signature as per the above specifications.
        """,
        input_variables=['file_content', 'issue_details', 'project_name', 'project_path', 'requirements_document', 'error_message', 'format_instructions'],
        partial_variables={
            "format_instructions": PydanticOutputParser(pydantic_object=FileFunctionSignatures).get_format_instructions()
        }
    )

    unit_test_generation_for_issue_prompt: PromptTemplate = PromptTemplate(
        template="""
        You are a skilled software developer specializing in unit test case generation. Your task 
        is to create comprehensive unit test cases for the functionalities that require testing. 
        In a test-driven development (TDD) environment, you play a crucial role in generating the 
        unit test cases first, which will guide the user in developing their functionalities to 
        comply with these tests. You are collaborating with a team to complete an end-to-end project 
        requested by a user.

        **Project Information:**
        - **Project Name:** '{project_name}'
        - **Project Path:** '{project_path}'

        **Business Logic:**
        Below is the current business logic of the file that you will be working with:
        ```
        {file_content}
        ```

        **Issue Details:**
        Here are the details of the issue related to the business logic:
        ```
        {issue_details}
        ```

        **Project Overview and Guidelines:**
        Below is a detailed overview of the project, including essential information and a set of 
        guidelines that must be strictly followed during the development process. These guidelines 
        have been meticulously designed by your team lead to ensure the highest quality of work:
        ```
        {requirements_document}
        ```

        **Error Handling:**
        Error messages will only be present if there is an issue with your previous response:
        ```
        {error_message}
        ```

        **Formatting Instructions:**
        Follow these formatting instructions when defining the unit test cases:
        ```
        {format_instructions}
        ```

        **Function Signatures:**
        Here are the function signatures dictionary, where the key contains the path for each function, 
        and the value includes the function skeleton, which consists of the function name, input parameters, 
        return type, and function description for which you need to create unit test cases:
        ```
        {functions_skeleton}
        ```

        **Instructions for Unit Test Case Generation:**
        - Write clear and comprehensive unit tests for each function specified in the provided function signatures.
        - Ensure that your tests cover all relevant scenarios, including edge cases and potential failure points.
        - Use appropriate assertions to validate the expected behavior of each function.

        Please complete the task by generating the unit test cases according to the specifications outlined above.
        """,
        input_variables=['project_name', 'project_path', 'file_content', 'issue_details', 'requirements_document', 'error_message', 'functions_skeleton'],
        partial_variables={
            "format_instructions": PydanticOutputParser(pydantic_object=TestCodeGeneration).get_format_instructions()
        }
    )
