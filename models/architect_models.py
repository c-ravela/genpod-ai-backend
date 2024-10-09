"""
This module defines the data model for the output of the Architect agent in 
the form of a Requirements Document.

"""
from pydantic import BaseModel, Field, field_validator
from typing_extensions import ClassVar


class ProjectDetails(BaseModel):
    """
    This class encapsulates the essential details of a project. It includes fields 
    to describe the project name and the project's folder structure. These details 
    provide a high-level overview of the project and its organization.
    """

    project_name: str = Field(
        description="The name of the project",
        required=True
    )

    # project_folder_structure: str = Field(
    #     description="The folder structure to be adhered to for the project",
    #     required=True
    # )

class TaskOutput(BaseModel):
    """
    This class represents the output of a task. It includes fields to indicate 
    whether additional information is needed to complete the task, the question 
    to ask for additional information, and the content of the requested information.
    """
    
    is_add_info_needed: bool = Field(
        description="Indicates whether additional information is needed to complete a task.",
        required=True
    )

    question_for_additional_info: str = Field(
        description="The question to ask when additional information is needed."
    )

    content: str = Field(
        description="The content of the requested information."
    )

class TasksList(BaseModel):
    """
    The TasksList class is a Pydantic model that represents a list of tasks for a project. 
    Each task in the list provides sufficient context and detailed information crucial for 
    the task completion process.
    """
    
    tasks: list[str] = Field(
        description="The list of tasks derived from the detailed requirements, "
        "each providing sufficient context with detailed information crucial for "
        "the task completion process", 
        required=True,
    )

    description: ClassVar[str] = "Schema representing a list of tasks derived from the project requirements."

    @field_validator("tasks")
    def check__tasks(cls, value):
        if not isinstance(value, list):
            raise TypeError(f"Expected 'tasks' to be of type list but received {type(value).__name__}.")

        if not value:
            raise ValueError(f"The 'tasks' list received from the previous response is empty. Received: {value}, Expected: Non empty list of strings.")
   
class QueryResult(BaseModel):
    """
    This model represents the result of a query or question. It contains information 
    about whether an answer was found and what the answer is.
    """

    is_answer_found: bool = Field(
        description="Indicates if an answer was found or provided in response to the question",
        required=True
    )

    response_text: str = Field(
        description="The response provided to the user's question"
    )

    description: ClassVar[str] = "Schema representing the result of a query or question."
