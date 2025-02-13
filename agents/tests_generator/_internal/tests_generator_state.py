"""TestCoder State

Agent graph state
"""

from typing import Dict

from pydantic import Field

from core.state import BaseInputState, BaseOutputState, BaseState
from models.models import PlannedIssue, PlannedTask, RequirementsDocument
from models.tests_generator_models import FileFunctionSignatures


class TestCoderInput(BaseInputState):
    """Represents the input state for the test coder."""

    project_name: str = Field(
        description="The name of the project."
    )
    requirements_document: RequirementsDocument = Field(
        description="The project's requirements document."
    )
    current_planned_task: PlannedTask = Field(
        default_factory=PlannedTask,
        description="The planned task currently under review, serving as a planning focus."
    )
    current_planned_issue: PlannedIssue = Field(
        default_factory=PlannedIssue,
        description="The planned issue currently under review, serving as a planning focus."
    )


class TestCoderOutput(BaseOutputState):
    """Represents the output state from the test coder."""

    current_planned_task: PlannedTask = Field(
        default_factory=PlannedTask,
        description="The planned task currently under review, serving as a planning focus."
    )
    current_planned_issue: PlannedIssue = Field(
        default_factory=PlannedIssue,
        description="The planned issue currently under review, serving as a planning focus."
    )
    test_code: Dict[str, str] = Field(
        description=(
            "The complete, well-documented unit test code adhering to the requested programming language "
            "and framework standards."
        )
    )
    function_signatures: FileFunctionSignatures = Field(
        description="Detailed function skeleton for the code."
    )


class TestCoderState(BaseState):
    """Maintains the overall state for the test coder, including both input and output details."""

    project_name: str = Field(
        default="",
        description="The name of the project."
    )
    requirements_document: RequirementsDocument = Field(
        default_factory=RequirementsDocument,
        description="The project's requirements document."
    )
    current_planned_task: PlannedTask = Field(
        default_factory=PlannedTask,
        description="The planned task currently under review, serving as a planning focus."
    )
    current_planned_issue: PlannedIssue = Field(
        default_factory=PlannedIssue,
        description="The planned issue currently under review, serving as a planning focus."
    )
    test_code: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "The complete, well-documented unit test code adhering to the requested programming language "
            "and framework standards."
        )
    )
    function_signatures: FileFunctionSignatures = Field(
        default_factory=FileFunctionSignatures,
        description="Detailed function skeleton for the code."
    )

    # internal
    current_test_generation: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Intermediate data related to the current test generation process, including function signatures "
            "and generated code."
        )
    )
