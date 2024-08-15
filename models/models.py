"""
This module, `models.py`, contains various data models used throughout the project.

Each class in this module represents a different data model, with each model 
capturing a specific set of information required for the project. These models
are used to structure the data in a consistent and organized manner, enhancing 
the readability and maintainability of the code.
"""
from pydantic import BaseModel, Field

from models.constants import Status
from utils.task_utils import generate_task_id


class Task(BaseModel):
    """
    A data model representing a task and its current state within a project
    or workflow.
    """
    task_id: str = Field(
        description="A unique task id to track and access current task and previous tasks",
        default_factory=generate_task_id
    )

    description: str = Field(
        description="A brief description outlining the objective of the task",
        default="",
        required=True
    )

    task_status: Status = Field(
        description="The current status indicating the progress of the task",
        default= Status.NONE,
        required=True
    )

    additional_info: str = Field(
        description="Additional info requested.",
        default=""
    )

    question: str = Field(
        description="Question to supervisor if additional information is needed"
        " to proceed with task execution.",
        default=""
    )

    remarks: str = Field(
        description="A field for notes on the task's status. If the task is "
        "abandoned, state the reason here.",
        default=""
    )

class RequirementsDocument:
    """
    This class encapsulates the various requirements of a project. 
    """

    project_details: str # A brief description of the project
    architecture: str # Details about the system's architecture
    folder_structure: str # Description of the project's directory or folder structure
    microservice_design: str # Design details of the microservices used in the project
    task_description: str # Overview of the tasks involved in the project
    standards: str # Coding standards and conventions followed in the project
    implementation_details: str  # Detailed description of the implementation process
    license_details: str # Information about the project's licensing

    def test(self):
        print("callable")