"""
Coder State

Defines the Agent's graph state for the CoderAgent.
"""
from typing import Dict, List

from pydantic import Field

from core.state import BaseInputState, BaseOutputState, BaseState
from models.coder_models import CodeGenerationPlan
from models.models import (Issue, PlannedIssue, PlannedTask,
                           RequirementsDocument)


class CoderInput(BaseInputState):
    """Represents the input state for the coder component."""

    project_name: str = Field(
        description="The name of the project being developed."
    )
    requirements_document: RequirementsDocument = Field(
        description="The document outlining the project's functional and non-functional requirements."
    )
    license_url: str = Field(
        description="The URL where the project's license file can be downloaded."
    )
    license_header: str = Field(
        description="The license header to include at the top of each source file."
    )
    functions_skeleton: Dict = Field(
        description="A blueprint detailing the structure and signatures of functions to be implemented."
    )
    test_code: Dict = Field(
        description="Complete, well-documented unit test code that adheres to the specified standards and frameworks."
    )
    current_planned_task: PlannedTask = Field(
        default_factory=PlannedTask,
        description="The task that is currently planned and being executed."
    )
    current_planned_issue: PlannedIssue = Field(
        default_factory=PlannedIssue,
        description="The issue that is currently planned for investigation or resolution."
    )
    current_issue: Issue = Field(
        default_factory=Issue,
        description="The issue object representing the current problem under investigation."
    )


class CoderOutput(BaseOutputState):
    """Represents the output state of the coder component."""

    current_planned_task: PlannedTask = Field(
        default_factory=PlannedTask,
        description="The currently planned task in the output state."
    )
    current_planned_issue: PlannedIssue = Field(
        default_factory=PlannedIssue,
        description="The currently planned issue being addressed."
    )
    current_issue: Issue = Field(
        default_factory=Issue,
        description="The issue object representing the current problem being resolved."
    )
    code_generation_plan_list: List[CodeGenerationPlan] = Field(
        description="A collection of generated code plans detailing the outcomes of the code generation process."
    )


class CoderState(BaseState):
    """Represents the overall state of the coder component."""

    current_planned_task: PlannedTask = Field(
        default_factory=PlannedTask,
        description="The task currently being executed."
    )
    current_planned_issue: PlannedIssue = Field(
        default_factory=PlannedIssue,
        description="The issue currently planned for resolution."
    )
    current_issue: Issue = Field(
        default_factory=Issue,
        description="The issue object representing the current problem under investigation."
    )
    code_generation_plan_list: List[CodeGenerationPlan] = Field(
        default_factory=list,
        description="A collection of code generation plans that document the output of the code generation process."
    )
    project_name: str = Field(
        description="The name of the project being developed."
    )
    requirements_document: RequirementsDocument = Field(
        default_factory=RequirementsDocument,
        description="The document that specifies the functional and non-functional requirements of the project."
    )
    license_url: str = Field(
        default="",
        description="The URL from which the project's license file can be downloaded."
    )
    license_header: str = Field(
        default="",
        description="The license header that should be included in every source file."
    )
    functions_skeleton: Dict = Field(
        default_factory=dict,
        description="A detailed blueprint outlining the structure and expected behavior of the project functions."
    )
    test_code: Dict = Field(
        default_factory=dict,
        description="A set of well-documented unit tests that comply with the specified standards and frameworks."
    )

    # internal
    is_license_file_downloaded: bool = Field(
        default=False,
        description="Indicates whether the license file has been successfully downloaded."
    )
