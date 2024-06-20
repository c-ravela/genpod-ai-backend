"""
Archiect Agent

pydantic models
"""
from typing_extensions import ClassVar

from pydantic import Field
from pydantic import BaseModel

from enum import Enum

class RequirementsDoc(BaseModel):
    """
    Requirements Document
    """

    project_name: str = Field(description="Project name that the user has assigned you to work on", required=True)
    well_documented: str = Field(description="Well built requirements document from the user input", required=True)
    tasks: str = Field(description="Spilt the detailed requirements into list of tasks with as much context as possible that are crucial to follow during completion", required=True)
    project_folder_structure: str = Field(description="Project folder structure to follow.", required=True)
    next_task: str = Field(description="Next Task to do with all the functional and non functional details related to that task", required=True)
    call_next: str = Field(description="name of the node that the flow has to follow next", required=True)
    project_state: str = Field(description="status of the project. whether all the tasks needed for project completion are completed or not", required=True)

    description: ClassVar[str] = "Schema of what all documents should be generated."

class TaskInfo(BaseModel):
    """
    """

    task: str
    state: str

class TaskState(Enum):
    NEW: str = 'NEW'
    INPROGRESS: str = 'INPROGRESS'
    AWAITING: str = 'AWAITING'
    COMPLETED: str = 'COMPLETED'