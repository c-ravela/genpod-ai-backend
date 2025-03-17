""" Graph State for Planner Agent """

from typing import Annotated, List, Literal, TypedDict

from agents.base.base_state import BaseState
from models.models import Issue, PlannedIssuesQueue, PlannedTaskQueue, Task


class PlannerState(TypedDict):
    """
    Represents the state of the Planner Agent.

    Attributes:
        project_status (str): Current status of the project (e.g., executing, resolving).
        project_path (str): File system path where the project resides.
        context (str): Information including the requirements document and relevant retrieval data.
        current_task (Task): The task currently being processed.
        current_issue (Issue): The issue currently being addressed by the planner.
        planned_tasks (PlannedTaskQueue): Queue containing planned tasks broken down by the planner.
        planned_issues (PlannedIssuesQueue): Queue containing planned issues prepared by the planner.
        mode (Literal): Indicates whether the planner is working on tasks or issues.
        planned_backlogs (List[str]): Internal field storing the list of identified backlogs.
        file_count (int): Internal field tracking the number of files written during the session.
    """
    # @in
    project_status: Annotated[
        str, 
        BaseState.in_field("Current status of the project (e.g., executing, resolving).")
    ]

    # @in
    project_path: Annotated[
        str,
        BaseState.in_field("File system path where the project resides.")
    ]

    # @in
    context: Annotated[
        str,
        BaseState.in_field("Requirements document and other retrieval information.")
    ]

    # @inout
    current_task: Annotated[
        Task,
        BaseState.inout_field("The task currently being processed.")
    ]

    # @inout
    current_issue: Annotated[
        Issue,
        BaseState.inout_field("The issue currently being addressed by the planner.")
    ]

    # @out
    planned_tasks: Annotated[
        PlannedTaskQueue,
        BaseState.out_field("Queue containing work packages planned by the planner.")
    ]

    # @out
    planned_issues: Annotated[
        PlannedIssuesQueue,
        BaseState.out_field("Queue containing planned issues prepared by the planner.")
    ]

    # @internal
    mode: Annotated[
        Literal['preparing_planned_tasks', 'preparing_planned_issues'],
        BaseState.internal_field(
            """
            Mode explanation:
                - 'preparing_planned_tasks': Breaking down a general task into smaller, manageable planned tasks.
                - 'preparing_planned_issues': Preparing planned issues from a given issue, potentially requiring unit test case generation.
            """
        )
    ]

    # @internal
    planned_backlogs: Annotated[
        List[str],
        BaseState.internal_field("List of backlogs identified for planning tasks.")
    ]

    # @internal
    file_count: Annotated[
        int,
        BaseState.internal_field("Tracks the number of files written during the session.")
    ]
