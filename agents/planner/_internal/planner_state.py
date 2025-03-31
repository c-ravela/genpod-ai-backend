from typing import Any, Dict, List, Set

from pydantic import Field

from core.state import BaseInputState, BaseOutputState, BaseState
from models import (Issue, IssuesQueue, PlannedIssuesQueue, PlannedTaskQueue,
                    RequirementsDocument, TaskQueue)


class PlannerInput(BaseInputState):
    """
    Input model for the planning process.

    Attributes:
        deliverable_list (TaskQueue): A queue of deliverable descriptions to be used for generating tasks.
        issue_list (IssuesQueue): A queue of issues that require planning and further analysis.
        requirements_document (RequirementsDocument): A document outlining both the functional and non-functional project requirements.
        human_feedback (str): Reviewer feedback containing instructions or suggestions for updating work packages.
        additional_information (str): Extra contextual or system state information to support the planning process.
        current_issue (Issue): The issue currently under review that serves as the focal point for planning.
    """
    deliverable_list: TaskQueue = Field(
        default_factory=TaskQueue,
        description="Queue of deliverable descriptions to be used for generating tasks."
    )
    issue_list: IssuesQueue = Field(
        default_factory=IssuesQueue,
        description="Queue of issues that require planning. (Replace 'dict' with a dedicated Issue model if available.)"
    )
    requirements_document: RequirementsDocument = Field(
        description="Document outlining both functional and non-functional project requirements."
    )
    human_feedback: str = Field(
        default="",
        description="Reviewer feedback containing instructions or suggestions for updating work packages."
    )
    additional_information: str = Field(
        default="",
        description="Extra contextual or system state information to support the planning process."
    )
    current_issue: Issue = Field(
        default_factory=Issue,
        description="The issue currently under review that serves as the focal point for planning."
    )


class PlannerOutput(BaseOutputState):
    """
    Output model for the planning process.

    Attributes:
        planned_tasks (PlannedTaskQueue): A queue of work packages (tasks) generated as a result of planning.
        planned_issues (PlannedIssuesQueue): A queue of issues that have been processed and planned.
        current_issue (Issue): The issue that was actively analyzed during planning.
        deliverable_list (TaskQueue): A queue of deliverable descriptions provided for task planning.
        issue_list (IssuesQueue): A queue of issues considered during the planning process.
    """
    planned_tasks: PlannedTaskQueue = Field(
        default_factory=PlannedTaskQueue,
        description="Queue of work packages (tasks) generated as a result of planning."
    )
    planned_issues: PlannedIssuesQueue = Field(
        default_factory=PlannedIssuesQueue,
        description="Queue of issues that have been processed and planned."
    )
    current_issue: Issue = Field(
        default_factory=Issue,
        description="The issue that was actively analyzed during planning."
    )
    deliverable_list: TaskQueue = Field(
        default_factory=TaskQueue,
        description="Queue of deliverable descriptions provided for task planning."
    )
    issue_list: IssuesQueue = Field(
        default_factory=IssuesQueue,
        description="Queue of issues considered during the planning process. (Replace 'dict' with a dedicated Issue model if available.)"
    )



class PlannerState(BaseState):
    """
    Represents the complete state of the planning process.

    This model tracks all inputs, outputs, and internal progress for task and issue planning. It includes
    queues for deliverables and issues, a record of processed items, the project requirements, reviewer feedback,
    and the generated work packages along with their associated planned backlogs.

    Attributes:
        deliverable_list (TaskQueue): Queue of deliverable descriptions used for generating tasks.
        issue_list (IssuesQueue): Queue of issues that require planning.
        processed_item_ids (Set[str]): Set of IDs for deliverables or issues that have already been processed.
        requirements_document (RequirementsDocument): The project's requirements document covering both functional and non-functional needs.
        human_feedback (str): Reviewer feedback with recommendations for refining work packages.
        additional_information (str): Additional context or system details that support the planning process.
        current_issue (Issue): The issue currently under review.
        planned_tasks (PlannedTaskQueue): Queue of work packages (tasks) generated during planning.
        planned_issues (PlannedIssuesQueue): Queue of issues that have been processed during planning.
        planned_backlogs (List[Dict[str, Any]]): List of planned backlog entries mapping parent deliverable IDs to their corresponding backlog content.
    """
    deliverable_list: TaskQueue = Field(
        default_factory=TaskQueue,
        description="Queue of deliverable descriptions used for generating tasks."
    )
    issue_list: IssuesQueue = Field(
        default_factory=IssuesQueue,
        description="Queue of issues that require planning."
    )
    processed_item_ids: Set[str] = Field(
        default_factory=set,
        description="Set of IDs for deliverables or issues that have already been processed."
    )
    requirements_document: RequirementsDocument = Field(
        default_factory=RequirementsDocument,
        description="The project's requirements document covering both functional and non-functional needs."
    )
    human_feedback: str = Field(
        default='',
        description="Reviewer feedback with recommendations for refining work packages."
    )
    additional_information: str = Field(
        default='',
        description="Additional context or system details that support the planning process."
    )
    current_issue: Issue = Field(
        default_factory=Issue,
        description="The issue currently under review."
    )
    planned_tasks: PlannedTaskQueue = Field(
        default_factory=PlannedTaskQueue,
        description="Queue of work packages (tasks) generated during planning."
    )
    planned_issues: PlannedIssuesQueue = Field(
        default_factory=PlannedIssuesQueue,
        description="Queue of issues that have been processed during planning."
    )
    planned_backlogs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of planned backlog entries mapping parent deliverable IDs to their corresponding backlog content."
    )
