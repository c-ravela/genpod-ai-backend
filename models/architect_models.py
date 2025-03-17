"""
This module defines the data model for the output of the Architect agent in
the form of a Requirements Document.
"""
from typing import ClassVar, List

from pydantic import BaseModel, Field, field_validator


class ProjectDetails(BaseModel):
    """
    Represents the essential details of a project.
    """
    project_name: str = Field(
        description="The name of the project.",
    )

    # project_folder_structure: str = Field(
    #     description="The folder structure to be adhered to for the project",
    #     required=True
    # )


class TaskResponse(BaseModel):
    """
    This model represents the response output of a task.
    It encapsulates the content that answers the prompt.
    """

    content: str = Field(
        description="The response content for the prompt."
    )


class TaskList(BaseModel):
    """
    TaskList represents a collection of tasks for a project.
    
    Each task in the list provides the necessary context and details crucial for task completion.
    """
    tasks: List[str] = Field(
        description=(
            "A non-empty list of tasks derived from the detailed requirements. "
            "Each task provides sufficient context and detailed information required for task execution."
        )
    )

    SCHEMA_DESCRIPTION: ClassVar[str] = (
        "Schema representing a list of tasks derived from the project requirements."
    )

    @field_validator("tasks")
    def validate_tasks(cls, value: List[str]) -> List[str]:
        """
        Validates that the 'tasks' field is a non-empty list.

        Args:
            value (List[str]): The input list of tasks.

        Returns:
            List[str]: The validated list of tasks.

        Raises:
            TypeError: If the provided value is not a list.
            ValueError: If the list is empty.
        """
        if not isinstance(value, list):
            raise TypeError(f"Expected 'tasks' to be a list but received {type(value).__name__}.")
        if not value:
            raise ValueError("The 'tasks' list is empty. Expected a non-empty list of strings.")
        return value


class QueryResult(BaseModel):
    """
    This model represents the result of a query or question. It contains information
    about whether an answer was found and what the answer is.
    """

    is_answer_found: bool = Field(
        description="Indicates if an answer was provided to the question.",
        required=True
    )

    response_text: str = Field(
        description="The response provided to the user's question"
    )
