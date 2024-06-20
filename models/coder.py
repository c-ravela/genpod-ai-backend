"""
This module defines the data model for the output of the Coder agent. 

The Coder agent is responsible for completing tasks in a project. The output of 
the Coder agent includes information about the steps to complete a task, 
the files to be created, the location of the code, the actual code.
"""

from typing_extensions import ClassVar

from pydantic import Field
from pydantic import BaseModel

class CoderModel(BaseModel):
    """
    A data model representing the output of the Coder agent.

    This model includes various fields that capture the details of the task 
    completion process, such as the steps to complete the task, the files to
    be created, the location of the code, and the actual code.
    """

    steps_to_complete: str = Field(
        description="A breakdown of the main task into smaller, manageable"
        "steps. This could include creating individual files, setting up "
        "directories, writing functions, etc., depending on the nature of"
        "the main task.", 
        required=True
    )

    files_to_create: str = Field(
        description="List of files that need to be created as part of the task", 
        required=True
    )

    file_path: str = Field(
        description="Path where the code should be written, based on the "
        "project structure", 
        required=True
    )

    code: str = Field(
        description="The complete, well-documented code that adheres to all "
        "naming standards and is necessary to complete the task", 
        required=True
    )
    
    description: ClassVar[str] = "Schema representing the output from the "
    "Coder agent upon task completion."
