"""
This module, `models.py`, contains various data models used throughout the project.

Each class in this module represents a different data model, with each model 
capturing a specific set of information required for the project. These models
are used to structure the data in a consistent and organized manner, enhancing 
the readability and maintainability of the code.
"""

from pydantic import Field
from pydantic import BaseModel

class Task(BaseModel):
    """
    A data model representing a task and its current state within a project
    or workflow.
    """

    description: str = Field(
        description="A brief description outlining the objective of the task", 
        required=True
    )
    
    state: str = Field(
        description="The current state indicating the progress of the task", 
        required=True
    )
