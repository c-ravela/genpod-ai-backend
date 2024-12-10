"""TestCoder State

Agent graph state
"""

from typing import Annotated, Any, Dict, Literal, TypedDict

from agents.base.base_state import BaseState
from models.constants import ChatRoles, PStatus
from models.models import PlannedIssue, PlannedTask, RequirementsDocument
from models.tests_generator_models import FileFunctionSignatures


class TestCoderState(TypedDict):
    """Represents the state of the TestCoder agent."""

    # @in
    project_name: Annotated[
        str,
        BaseState.in_field("The name of the project.")
    ]

    # @in
    project_status: Annotated[
        PStatus,
        BaseState.in_field("The status of the project being generated.")
    ]

    # @in
    requirements_document: Annotated[
        RequirementsDocument,
        BaseState.in_field(
            "A detailed markdown document outlining the project's requirements, "
            "standards, and structure."
        )
    ]

    # @in
    project_path: Annotated[
        str,
        BaseState.in_field(
            "The full path to the project directory on the local filesystem."
        )
    ]

    # @inout
    current_planned_task: Annotated[
        PlannedTask,
        BaseState.inout_field(
            "The current task being executed, containing details such as description, "
            "status, and execution requirements."
        )
    ]
   
    # @inout
    current_planned_issue: Annotated[
        PlannedIssue,
        BaseState.inout_field("The current planned issue that team is working on.")
    ]
    
    # @inout
    messages: Annotated[
        list[tuple[ChatRoles, str]],
        BaseState.inout_field(
            "A chronological list of tuples representing the conversation history between "
            "the system, user, and AI. Each tuple contains a role identifier (e.g., 'AI', "
            "'tool', 'user', 'system') and the corresponding message."
        )
    ]

    # @out
    test_code: Annotated[
        Dict[str, str],
        BaseState.out_field(
            "The complete, well-documented working unit test code that adheres to all "
            "standards requested with the programming language, framework user requested",
        )
    ]
    
    # @out
    function_signatures: Annotated[
        FileFunctionSignatures,
        BaseState.out_field(
            "The well detailed function skeleton for the functions that are in the code."
        )
    ]

    # @internal
    mode: Annotated[
        Literal['test_code_generation', 'resolving_issues'],
        BaseState.internal_field(
            "Indicates the agent's current operational mode (e.g., generating test code or resolving issues)."
        )
    ]

    # @internal
    hasError: Annotated[
        bool,
        BaseState.internal_field("Flag indicating whether an error occurred during the process.")
    ]

    # @internal
    is_skeleton_generated: Annotated[
        bool,
        BaseState.internal_field("Flag indicating if the function skeleton has been generated successfully.")
    ]

    # @internal
    is_code_generated: Annotated[
        bool,
        BaseState.internal_field("Flag indicating if the test code has been generated successfully.")
    ]

    # @internal
    has_command_execution_finished: Annotated[
        bool,
        BaseState.internal_field("Flag indicating whether all generated commands have been executed.")
    ]

    # @internal
    is_skeleton_written_to_local: Annotated[
        bool,
        BaseState.internal_field("Flag indicating whether the function skeleton has been written to local files.")
    ]

    # @internal
    has_skeleton_been_written_locally: Annotated[
        bool,
        BaseState.internal_field(
             "Flag indicating whether the skeleton files have been saved to the local filesystem."
        )
    ]

    # @internal
    hasPendingToolCalls: Annotated[
        bool,
        BaseState.internal_field(
            "Flag indicating if there are pending external tool invocations required by the agent."
        )
    ]

    # @internal
    last_visited_node: Annotated[
        str,
        BaseState.internal_field(
            "The last node in the workflow visited by the agent, used for tracking progress."
        )
    ]

    # @internal
    error_message: Annotated[
        str,
        BaseState.internal_field("Details of the most recent error encountered by the agent.")
    ]

    # @internal
    current_test_generation: Annotated[
        Dict[str, Any],
        BaseState.internal_field(
            "Holds intermediate data related to the current test generation process, "
            "such as function signatures and generated code."
        )
    ]
