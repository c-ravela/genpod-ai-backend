""" Graph State for Planner Agent """
from typing import Dict, List

from typing_extensions import Annotated, TypedDict

from agents.base.base_state import BaseState
from models.models import Issue, PlannedIssuesQueue, PlannedTaskQueue, Task


class PlannerState(TypedDict):
    """
    Represents the state of our Planner Retriever.

    Attributes:
        deliverable: Individual deliverables identified by the Architect
        details: LLM generation of the minute details needed to complete each task
        response: list of Task packets to main all older responses.
    """
    # @in
    project_status: Annotated[
        str, 
        BaseState.in_field()
    ]

    # @in
    project_path: Annotated[
        str,
        BaseState.in_field()
    ]

    # @in
    context: Annotated[
        str,
        BaseState.in_field("Requirements document  and rag retrivial info.")
    ]

    # @inout
    current_task: Annotated[
        Task,
        BaseState.inout_field()
    ]

    current_issue: Annotated[
        Issue,
        BaseState.inout_field()
    ]

    # @out
    planned_tasks: Annotated[
        PlannedTaskQueue,
        BaseState.out_field("A list of work packages planned by the planner")
    ]

    # @out
    planned_issues: Annotated[
        PlannedIssuesQueue,
        BaseState.out_field("A list of planned issues")
    ]
