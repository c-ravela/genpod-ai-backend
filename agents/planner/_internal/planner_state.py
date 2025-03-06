from typing import Annotated, List, Literal, TypedDict

from pydantic import Field

from core.state import BaseInputState, BaseOutputState, BaseState
from models import (Issue, PlannedIssuesQueue, PlannedTaskQueue,
                    RequirementsDocument)


class PlannerInput(BaseInputState):
    """
    Input state for the planner.

    Attributes:
        requirements_document (RequirementsDocument): The requirements document.
        additional_information (str): Other retrieval information.
        current_issue (Issue): The current issue.
    """
    requirements_document: RequirementsDocument = Field(
        description="A comprehensive document detailing both the functional and non-functional requirements for the project."
    )

    additional_information: str = Field(
        default='',
        description="Supplementary contextual data or insights that support and enrich the requirements document."
    )

    current_issue: Issue = Field(
        default_factory=Issue,
        description="The specific issue currently under review or analysis, serving as a focal point for planning."
    )


class PlannerOutput(BaseOutputState):
    """
    Output state for the planner.

    Attributes:
        planned_tasks (PlannedTaskQueue): Queue containing work packages planned by the planner.
        planned_issues (PlannedIssuesQueue): Queue containing planned issues prepared by the planner.
        current_issue (Issue): The current issue.
    """
    planned_tasks: PlannedTaskQueue = Field(
        default_factory=PlannedTaskQueue,
        description="Queue containing work packages planned by the planner."
    )

    planned_issues: PlannedIssuesQueue = Field(
        default_factory=PlannedIssuesQueue,
        description="Queue containing planned issues prepared by the planner."
    )

    current_issue: Issue = Field(
        default_factory=Issue,
        description="The specific issue currently under review or analysis, serving as a focal point for planning."
    )


class PlannerState(BaseState):
    """
    State for the planner.

    Attributes:
        requirements_document (RequirementsDocument): The requirements document.
        additional_information (str): Other retrieval information.
        current_issue (Issue): The current issue.
        planned_tasks (PlannedTaskQueue): Queue containing work packages planned by the planner.
        planned_issues (PlannedIssuesQueue): Queue containing planned issues prepared by the planner.
    """
    requirements_document: RequirementsDocument = Field(
        default_factory=RequirementsDocument,
        description="requirements document"
    )

    additional_information: str = Field(
        default='',
        description="Supplementary contextual data or insights that support and enrich the requirements document."
    )

    current_issue: Issue = Field(
        default_factory=Issue,
        description="The specific issue currently under review or analysis, serving as a focal point for planning."
    )

    planned_tasks: PlannedTaskQueue = Field(
        default_factory=PlannedTaskQueue,
        description="Queue containing work packages planned by the planner."
    )

    planned_issues: PlannedIssuesQueue = Field(
        default_factory=PlannedIssuesQueue,
        description="Queue containing planned issues prepared by the planner."
    )

    # internal
    file_count: int = Field(
        default=0,
        description="Number of work packages generated so far."
    )

    planned_backlogs: List[str] = Field(
        default_factory=list,
        description="List of planned backlogs."
    )
