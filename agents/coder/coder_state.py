"""
Coder State

Defines the Agent's graph state for the CoderAgent.
"""
from typing import Annotated, Literal, TypedDict

from agents.base.base_state import BaseState
from models.coder_models import CodeGenerationPlan
from models.constants import ChatRoles
from models.models import (Issue, PlannedIssue, PlannedTask,
                           RequirementsDocument, Task)


class CoderState(TypedDict):
    """
    CoderState Class

    Represents the state structure for the CoderAgent. Encapsulates input, output,
    and internal fields required to manage the agent's operations and workflow.
    """

    # @in
    project_status: Annotated[
        str,
        BaseState.in_field(
            "The current status of the project, such as executing or resolving."
        )
    ]

    # @in
    project_name: Annotated[
        str,
        BaseState.in_field("The name of the project.")
    ]

    # @in
    requirements_document: Annotated[
        RequirementsDocument,
        BaseState.in_field(
            "A comprehensive, well-structured document in markdown format outlining "
            "the project's requirements. Serves as a guide for the development process."
        )
    ]

    # @in
    project_path: Annotated[
        str,
        BaseState.in_field(
            "The absolute file system path where the project is being generated. "
            "Includes all project-related files and directories."
        )
    ]

    # @in
    license_url: Annotated[
        str,
        BaseState.in_field("The URL from which the license file can be downloaded.")
    ]

    # @in
    license_text: Annotated[
        str,
        BaseState.in_field("The text of the license to be added to the project's files.")
    ]

    # @in
    functions_skeleton : Annotated[
        dict,
        BaseState.in_field(
            "A detailed skeleton of the functions in the code, serving as a blueprint "
            "for implementation."
        )
    ]

    # @in
    test_code: Annotated[
        dict,
        BaseState.in_field(
            "Complete and well-documented unit test code that adheres to user-specified "
            "standards and frameworks."
        )
    ]

    # @inout
    current_task: Annotated[
        Task,
        BaseState.inout_field(
            "The Task object currently in focus, representing the active task being worked on."
        )
    ]

    # @inout
    current_planned_task: Annotated[
        PlannedTask,
        BaseState.inout_field(
            "The PlannedTask object currently in focus, representing the task assigned to the coder."
        )
    ]
    
    # @inout
    current_planned_issue: Annotated[
        PlannedIssue,
        BaseState.inout_field("The planned issue currently being addressed by the team.")
    ]

    current_issue: Annotated[
        Issue,
        BaseState.inout_field("The Issue object representing the current issue under investigation.")
    ]

    # @inout
    messages: Annotated[
        list[tuple[ChatRoles, str]],
        BaseState.inout_field(
            "Chronological conversation history between system, user, and AI. Each entry contains "
            "a role identifier (e.g., 'AI', 'tool', 'user', 'system') and the corresponding message."
        )
    ]
    
    # @out
    code_generation_plan_list: Annotated[
        CodeGenerationPlan,
        BaseState.out_field(
            "A list of generated code plans, detailing the output of the code generation process."
        )
    ]

    # @internal
    mode: Annotated[
        Literal["code_generation", "general_task", "resolving_issues"],
        BaseState.internal_field("The current mode of the agent (e.g., code generation, general tasks, resolving issues).")
    ]

    # @internal
    is_code_generated: Annotated[
        bool, 
        BaseState.internal_field("Indicates whether code has been successfully generated.")
    ]

    # @internal
    has_command_execution_finished: Annotated[
        bool,
        BaseState.internal_field("Indicates whether command execution has completed.")
    ]

    # @internal
    has_code_been_written_locally: Annotated[
        bool,
        BaseState.internal_field("Indicates whether the generated code has been written to the local filesystem.")
    ]

    # @internal
    is_license_file_downloaded: Annotated[
        bool,
        BaseState.internal_field("Indicates whether the license file has been successfully downloaded.")
    ]

    # @internal
    is_license_text_added_to_files: Annotated[
        bool,
        BaseState.internal_field("Indicates whether license text has been added to the relevant files.")
    ]

    # @internal
    hasPendingToolCalls: Annotated[
        bool,
        BaseState.internal_field("Indicates whether there are pending tool calls that need to be addressed.")
    ]

    # @internal
    last_visited_node: Annotated[
        str,
        BaseState.internal_field("The last node visited in the graph, used for routing decisions.")
    ]

    # @internal
    error_message: Annotated[
        str,
        BaseState.internal_field("Stores any error message encountered during the agent's operations.")
    ]
