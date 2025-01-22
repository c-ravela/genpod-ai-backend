"""
"""
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from core.prompt import PromptWithConfig
from models.coder_models import CodeGenerationPlan


class CoderPrompts:

    code_generation_prompt: PromptWithConfig = PromptWithConfig(
        template=PromptTemplate(
            template="""
            As a skilled programmer, you play a critical role in delivering high-quality work for the project at hand. 
            Your task involves working on code generation, documentation, or other programming-related activities, 
            depending on the project requirements. Please ensure your work is well-documented, secure, optimized, and production-ready.

            **Project Overview:**
            - **Project Name:** '{project_name}'
            - **Project Path:** '{project_path}'

            **Guidelines:**
            Below is the set of detailed guidelines specified by your team lead. These guidelines are essential to follow 
            to maintain the highest standard and ensure the success of the project:
            - "{requirements_document}"

            **Scope Clarification:**
            1. **Code Generation Tasks:**  
            If the task involves generating code, function skeletons and unit test cases will be provided. Your job is to:
            - Implement the provided function skeletons.
            - Ensure the implementation passes the given unit test cases.
            - Write secure, optimized, and maintainable code.
            - Focus only on the required function implementations (do not include the unit test cases in your response).

            2. **Documentation or Comments:**  
            If your task involves writing documentation or comments, ensure that:
            - The content is clear, concise, and relevant to the provided code or project requirements.
            - Follow the formatting and style guidelines in the provided requirements document.
            
            3. **Setup or Configuration Tasks:**  
            - If your task involves setup, configuration, or managing dependencies:
            - Work on files like **`Dockerfile`, `package.json`, `requirements.txt`, or `*.yml`** as per the tasks needs.
            - Ensure that the configurations are correct, production-ready, and aligned with the project requirements.
            - Follow best practices for security, versioning, and compatibility.

            4. **Other Assigned Tasks:**  
            If the task falls outside of code generation (e.g., refactoring, analysis, etc.), follow the specific instructions 
            provided in the task description and align your work with the project's objectives.

            **Command Restrictions:**  
            Please **do not use pipe or command-combining symbols**. If required, break down commands into separate steps.

            **Error Handling:**  
            - If there are any issues with your response, you will receive an error message as feedback:  
            "{error_message}"

            **Formatting Instructions:**  
            - Follow these instructions carefully:  
            <instructions>
                {format_instructions}
            </instructions>
            
            **Your Task:**  
            - "{task}"

            **Function Skeletons (if applicable):**  
            - "{functions_skeleton}"

            **Unit Test Cases (if applicable):**  
            - "{unit_test_cases}"

            Please focus strictly on the assigned task and adhere to the provided instructions. Avoid adding unnecessary information 
            outside the scope of the task. Let's collaborate efficiently to deliver high-quality work.
            """,
            input_variables=['project_name', 'project_path', 'requirements_document', 'error_message', 'task', 'functions_skeleton', 'unit_test_cases'],
            partial_variables={
                "format_instructions": PydanticOutputParser(pydantic_object=CodeGenerationPlan).get_format_instructions()
            }
        ),
        enable_rag_retrival=True
    )

    issue_resolution_prompt: PromptWithConfig = PromptWithConfig(
        template=PromptTemplate(
            template="""
            As a skilled programmer, you are a key part of a team working to deliver a high-quality, end-to-end project. 
            Your responsibility is to develop well-documented, optimized, secure, and production-ready code. Focus solely 
            on resolving the assigned issue.

            Project Name: '{project_name}'
            Project Path: '{project_path}'

            Please note, error messages will only appear if there is an issue with your previous response:
            "{error_message}"

            Current content of the file at {file_path}:
            "{file_content}"
                
            You are now tasked with addressing the following issue in the project:
            "{issue}"

            If the issue involves changes to functionality, you will be provided with the relevant function signatures and 
            unit test code. Make sure to align your code changes with the provided function signatures and ensure that all unit tests pass.

            - **Function Signatures:** 
            ```
            {function_signatures}
            ```

            - **Unit Test Code:**
            ```
            {unit_test_code}
            ```

            **Important Notes:**
            - Focus only on the resolution of the assigned issue. Avoid making any changes that are not directly related to the issue at hand.
            - Ensure your solution adheres to the project's guidelines and requirements.
            
            Please adhere strictly to the following format when submitting your response:
            <instructions>
                {format_instructions}
            </instructions>

            """,
            input_variables=['project_name', 'project_path', 'error_message', 'issue', 'file_path', 'file_content', 'function_signatures', 'unit_test_code'],
            partial_variables={
                "format_instructions": PydanticOutputParser(pydantic_object=CodeGenerationPlan).get_format_instructions()
            }
        ),
        enable_rag_retrival=True
    )
