from typing import List, TypedDict
from pydantic import BaseModel
from models.enums import ProgressState

class TaskDetails(BaseModel):
    task: str
    task_status: ProgressState # ['INPROGRESS','HALT','COMPLETE']
    additional_info: str
    # Add any other fields you need for the task details