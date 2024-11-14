"""TestCoder State

Agent graph state
"""

from typing import Dict

from typing_extensions import Annotated, TypedDict

from agents.agent.state import State
from models.constants import ChatRoles, PStatus
from models.models import (Issue, PlannedIssue, PlannedTask,
                           RequirementsDocument, Task)
from models.tests_generator_models import FileFunctionSignatures


class TestCoderState(TypedDict):
    """
    """

    # @in
    project_name: Annotated[
        str,
        State.in_field(
            "The name of the project."
        )
    ]

    # @in
    project_status: Annotated[
        PStatus,
        State.in_field("The status of the project being generated.")
    ]

    # @in
    requirements_document: Annotated[
        RequirementsDocument,
        State.in_field(
            "A comprehensive, well-structured document in markdown format that outlines "
            "the project's requirements derived from the user's request. This serves as a"
            " guide for the development process."
        )
    ]

    # @in
    project_path: Annotated[
        str,
        State.in_field(
            "The absolute path in the file system where the project is being generated. "
            "This path is used to store all the project-related files and directories."
        )
    ]

    # @inout
    current_planned_task: Annotated[
        PlannedTask,
        State.inout_field(
            "The PlannedTask object currently in focus, representing the active task "
            "that coder need to work on."
        )
    ]
   
    # @inout
    current_planned_issue: Annotated[
        PlannedIssue,
        State.inout_field("The current planned issue that team is working on.")
    ]
    
    # @inout
    messages: Annotated[
        list[tuple[ChatRoles, str]],
        State.inout_field(
            "A chronological list of tuples representing the conversation history between "
            "the system, user, and AI. Each tuple contains a role identifier (e.g., 'AI', "
            "'tool', 'user', 'system') and the corresponding message."
        )
    ]

    # @out
    test_code: Annotated[
        Dict[str, str],
        State.out_field(
            "The complete, well-documented working unit test code that adheres to all "
            "standards requested with the programming language, framework user requested",
        )
    ]
    
    # @out
    function_signatures: Annotated[
        FileFunctionSignatures,
        State.out_field(
            "The well detailed function skeleton for the functions that are in the code."
        )
    ]
