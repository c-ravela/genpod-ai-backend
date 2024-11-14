""" Define the prompt template for the Planner """
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate

from models.planner_models import Segregation


class PlannerPrompts:
    task_breakdown_prompt = PromptTemplate(
        template="""
        You are an experienced Project Planner. Your task is to break down a project deliverable into 
        a list of actionable subtasks.

        You will be provided with:
        - The main deliverable
        - Additional context (if available)
        - Feedback on your previous response, if applicable (only included if the prior output was not in the correct format)
        
        Deliverable: `{deliverable}`
        Additional context: `{context}`
        Feedback: `{feedback}`

        **Format Instructions:**
        - provide a list of actionable subtasks needed to complete this deliverable.
        - Provide your response as a raw Python list, exactly in the format shown below.
        - Do not include any markdown, code blocks, or additional text.
        - The output must match this example exactly, including the square brackets:
        "['subtask1', 'subtask2', 'subtask3']"

        **Important:**
        - Ensure the response reflects the required subtasks, whether it is a single task or multiple tasks.
        - The output must be directly convertible using `ast.literal_eval()`.

        Your goal is to provide a backlog of subtasks in the correct format for the provided deliverable.
        """,
        input_variables=["deliverable", "context", "feedback"]
    )

    detailed_requirements_prompt = PromptTemplate(
        template="""
        You are an experienced Project Planner. Your task is to analyze the given backlog item and 
        provide detailed technical requirements in the specified JSON format. 

        If additional information is needed, ask specific questions.
        Feedback will only be provided if your previous response did not adhere to the correct format.

        Backlog Item: {backlog}
        Deliverable: {deliverable}
        Additional Context: {context}
        Feedback: {feedback}

        **Instructions:**
        - Refer to the sample requirements document below for guidance. If you have sufficient information, 
        provide the detailed technical requirements as a JSON object with the structure outlined below. 

        Avoid adding generic comments within the JSON object. Use strict JSON format for comments about any object:
        ```json
        {{
            "description": "Detailed description of the task",
            "name": "Name of the service or component",
            "language": "Programming language to be used",
            "restConfig": {{
                "server": {{
                    "DB": "Database type",
                    "uri_string": "<connection string>",
                    "port": "<Port number>",
                    "resources": [
                        {{
                            "name": "Resource name",
                            "allowedMethods": ["GET", "POST", "PUT", "DELETE"],
                            "fields": {{
                                "FieldName": {{
                                    "datatype": "Data type of the field"
                                }}
                                ...
                            }}
                        }}
                        ...
                    ]
                }},
                "framework": "Framework to be used"
            }}
        }}
        ```

        - If additional information is required, respond with a JSON object containing a single, detailed question.
        ```json
        {{
            "question": "A single, detailed question that covers all the information needed to proceed with the technical requirements"
        }}
        ```
        
        **Remember:**
        - Focus on technical aspects and implementation details.
        - Consider architectural decisions, coding standards, and best practices.
        - Include any necessary API specifications, database schema changes, or UI/UX considerations.
        - If critical technical information is missing, ask specific questions to clarify.
        - Ensure that all requirements are clear, measurable, and testable from a development perspective.
        """,
        input_variables=["backlog", "deliverable", "context", "feedback"]
    )

    segregation_prompt: PromptTemplate = PromptTemplate(
        template="""
        Objective:
        You are an intelligent assistant designed to assess whether completing a work package requires writing any functions. Use contextual understanding to accurately evaluate the tasks within the work package.

        Instructions:

        Identify Function Requirement:
            Determine whether any part of the work package involves writing functions (code blocks that perform specific tasks) in the given programming language.

        Assessment Criteria:
            Requires Writing Functions: The task involves creating new functions, modifying existing ones, or utilizing functions to achieve specific objectives.
            Does Not Require Writing Functions: The task does not involve writing or modifying functions, but may involve other activities such as configuration, documentation, or design.

        Response Format:
            Clearly state whether the work package requires writing functions or not.
            Provide a brief explanation if necessary to justify the assessment.

        The instructions for formatting are as follows:
        {format_instructions}

        This is the work package you have to classify using the description and the details provided classisfy 

        "{work_package}"
        """,
        input_variables=['work_package'],
        partial_variables= {
            "format_instructions": PydanticOutputParser(pydantic_object=Segregation).get_format_instructions()
        }
    )
    
    issues_segregation_prompt: PromptTemplate = PromptTemplate(
        template="""
        You are an intelligent assistant designed to assess whether fixing an issue involves 
        changes or creation of functions in the given file. Below are the file contents and issue details. 
        Based on the information provided, return your assessment in the following format:

        File Content:
        {file_content}

        Issue Details:
        {issue_details}

        {format_instruction}
        """,
        input_variables=['file_content', 'issue_details'],
        partial_variables={
            "format_instruction": PydanticOutputParser(pydantic_object=Segregation).get_format_instructions()
        }
    )
