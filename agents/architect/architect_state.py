"""
Architect State Module

This module defines the `ArchitectState` class, a `TypedDict` representing 
the state of the Architect agent. It also includes functions to manipulate the 
state with logging for better traceability.
"""
from typing import Annotated, Literal, TypedDict

from agents.base.base_state import BaseState
from models.constants import ChatRoles
from models.models import RequirementsDocument, Task, TaskQueue


class ArchitectState(TypedDict): 
    """
    ArchitectState Class

    This class encapsulates the state of the Architect agent, providing a 
    snapshot of the ongoing project's status and progress. 

    Attributes:
        original_user_input (str): The original set of requirements provided by the user, 
        serving as the foundation for the project.

        user_requested_standards (str): The specific standards or protocols the user has 
        requested to be implemented in the project, which could include coding standards, 
        design patterns, or industry-specific standards.

        project_status (str): An enumerated value reflecting the project's current lifecycle 
        stage, providing real-time tracking of project progress.

        project_path (str): The absolute path in the file system where the project 
        is being generated. This path is used to store all the project-related files and 
        directories.

        license_text (str): The text of the license provided by the user. This text outlines 
        the terms and conditions under which the project can be used, modified, and distributed.

        messages (list[tuple[ChatRoles, str]]): A chronological list of tuples representing the 
        conversation history between the system, user, and AI. Each tuple contains a role 
        identifier (e.g., 'AI', 'tool', 'user', 'system') and the corresponding message.
        
        current_task (Task): The Task object currently in focus, representing the active task 
        that team members are working on.

        project_name (str): The name of the project.

        requirements_document (str): A comprehensive, well-structured document in markdown 
        format that outlines the project's requirements derived from the user's request. 
        This serves as a guide for the development process.

        tasks (list[Task]): A list of Task objects, each encapsulating a distinct unit of work 
        necessary for the project's completion. These tasks are meant to be carried out by the 
        entire team collectively.

        query_answered (bool): A boolean flag indicating whether the task has been answered
    """
    # @in 
    original_user_input: Annotated[
        str,
        BaseState.in_field("User's requirements for the project.")
    ]

    # @in
    user_requested_standards: Annotated[
        str,
        BaseState.in_field("Standards or protocols requested by the user.")
    ]

    # @in
    project_status: Annotated[
        str,
        BaseState.in_field("Lifecycle stage of the project.")
    ]

    # @in
    project_path: Annotated[
        str,
        BaseState.in_field("Filesystem path for project-related files.")
    ]
    
    # @in
    license_text: Annotated[
        str,
        BaseState.in_field("License terms provided by the user.")
    ]

    # @inout
    messages: Annotated[
        list[tuple[ChatRoles, str]], 
        BaseState.inout_field("Chronological conversation history between agents.")
    ]

    # @inout
    current_task: Annotated[
        Task,
        BaseState.inout_field("Active task being processed.")
    ]

    # @out
    project_name: Annotated[
        str, 
        BaseState.out_field(
            "The name of the project."
        )
    ]

    # @out
    requirements_document: Annotated[
        RequirementsDocument, 
        BaseState.out_field("Markdown document of project requirements.")
    ]

    # @out
    tasks: Annotated[
        TaskQueue,
        BaseState.out_field("Queue of tasks required for the project.")
    ]

    # @out
    query_answered: Annotated[
        bool,
        BaseState.out_field("Indicates if the current query/task is resolved.")
    ]

    # @internal
    mode: Annotated[
        Literal["information_gathering", "document_generation"],
        BaseState.internal_field(
            "Operational mode: 'information_gathering' for queries, 'document_generation' for requirement creation."
        )
    ]

    # @internal
    generation_step: Annotated[
        int,
        BaseState.internal_field("Current step in the document generation process.")
    ]

    # @internal
    has_error_occured: Annotated[
        bool,
        BaseState.internal_field("Indicates if an error has occurred.")
    ]

    # @internal
    are_tasks_seperated: Annotated[
        bool,
        BaseState.internal_field("Indicates if tasks have been separated into a list.")
    ]

    # @internal
    is_additional_info_provided: Annotated[
        bool,
        BaseState.internal_field("Indicates if additional information was supplied.")
    ]

    # @internal
    is_requirements_document_generated: Annotated[
        bool,
        BaseState.internal_field("Indicates if the requirements document is generated.")
    ]

    # @internal
    is_requirements_document_saved: Annotated[
        bool,
        BaseState.internal_field("Indicates if the requirements document is saved.")
    ]

    # @internal
    is_additional_info_requested: Annotated[
        bool,
        BaseState.internal_field("Indicates if additional information is being requested.")
    ]

    # @internal
    are_project_details_provided: Annotated[
        bool,
        BaseState.internal_field("Indicates if project details are supplied.")
    ]

    # @internal
    last_visited_node: Annotated[
        str,
        BaseState.internal_field("The last graph node visited.")
    ]

    # @internal
    error_message: Annotated[
        str,
        BaseState.internal_field("Error message if an error occurred.")
    ]
