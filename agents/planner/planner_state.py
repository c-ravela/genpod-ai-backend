""" Graph State for Planner Agent """
from typing import Dict, List

from typing_extensions import TypedDict

from models.models import Task


class PlannerState(TypedDict):
    """
    Represents the state of our Planner Retriever.

    Attributes:
        deliverable: Individual deliverables identified by the Architect
        details: LLM generation of the minute details needed to complete each task
        response: list of Task packets to main all older responses.
    """

    deliverable: List[str]
    backlogs: List[str]
    generation: List[str]
    response: List[Task]
    deliverable_backlog_map: Dict[str, List[str]]
    current_task: Task
    backlog_requirements: Dict[str,str]
    generated_project_path: str
