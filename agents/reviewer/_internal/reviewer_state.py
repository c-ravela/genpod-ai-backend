
from pydantic import Field

from core.state import BaseInputState, BaseOutputState, BaseState
from models import RequirementsDocument
from models.models import IssuesQueue


class ReviewerInput(BaseInputState):
    """
    Represents the input state for the reviewer agent.

    Attributes:
        project_name (str): Name of the project.
        license_header (str): License text to be added at the top of each generated file.
        requirements_document (RequirementsDocument): Requirements documents for the project.
    """
    project_name: str = Field(
        description="Name of the project"
    )
    license_header: str = Field(
        default="",
        description="License text to be added at the top of each generated file."
    )
    requirements_document: RequirementsDocument = Field(
        description="Requirements documents for the project"
    )


class ReviewerOutput(BaseOutputState):
    """
    Represents the output state for the reviewer agent.

    Attributes:
        issues (IssuesQueue): List of issues found during the review process.
    """
    issues: IssuesQueue = Field(
        description="List of issues found during the review process."
    )


class ReviewerState(BaseState):
    """
    Represents the overall state for the reviewer agent.

    Attributes:
        project_name (str): Name of the project.
        license_header (str): License text to be added at the top of each generated file.
        requirements_document (RequirementsDocument): Requirements documents for the project.
        issues (IssuesQueue): List of issues found during the review process.
    """
    project_name: str = Field(
        default="",
        description="Name of the project"
    )
    license_header: str = Field(
        default="",
        description="License text to be added at the top of each generated file."
    )
    requirements_document: RequirementsDocument = Field(
        default_factory=RequirementsDocument,
        description="Requirements documents for the project"
    )
    issues: IssuesQueue = Field(
        default_factory=IssuesQueue,
        description="List of issues found during the review process."
    )
