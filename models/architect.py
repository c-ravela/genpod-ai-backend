"""
This module defines the data model for the output of the Architect agent in 
the form of a Requirements Document.

The Requirements Document captures the details of the project requirements, 
such as the project name, a well-documented requirements document, a list of 
tasks derived from the requirements, the project folder structure to follow. 
Each of these details is represented as a field in the `RequirementsDoc` class.
"""

from typing_extensions import ClassVar

from pydantic import Field
from pydantic import BaseModel

class RequirementsDoc(BaseModel):
    """
    A data model representing the output of the Architect agent in the form
    of a Requirements Document.

    This model includes various fields that capture the essential details of 
    the project requirements, such as the project name, a well-documented 
    requirements document, a list of tasks derived from the requirements, and
    the project folder structure to follow.
    """

    project_name: str = Field(
        description="The name of the project assigned by the user", 
        required=True
    )

    well_documented: str = Field(
        description="A comprehensive requirements document constructed from"
        " the user's input in a markdown format.", 
        required=True
    )

    tasks: list[str] = Field(
        description="The list of tasks derived from the detailed requirements, "
        "each providing sufficient context with detailed information crucial for "
        "the task completion process", 
        required=True
    )

    project_folder_structure: str = Field(
        description="The folder structure to be adhered to for the project", 
        required=True
    )
   
    description: ClassVar[str] = "Schema representing the documents to be "
    "generated based on the project requirements."

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
