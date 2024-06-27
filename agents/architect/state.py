"""Architect State

This module contains the ArchitectState class which is a TypedDict representing 
the state of the Architect agent. It also includes functions to manipulate the 
state.
"""

from typing_extensions import TypedDict
from typing_extensions import Annotated

from models.models import Task
from models.constants import Status

class ArchitectState(TypedDict): 
    """
    ArchitectState Class

    This class encapsulates the state of the Architect agent, providing a 
    snapshot of the ongoing project's status and progress. 

    Attributes:
        user_request (str): The original set of requirements provided by the user, 
        serving as the foundation for the project.

        user_requested_standards (str): The specific standards or protocols the user has 
        requested to be implemented in the project, which could include coding standards, 
        design patterns, or industry-specific standards.

        project_name (str): The name of the project.

        project_folder_structure (str): The organized layout of directories and subdirectories 
        that form the project's file system, adhering to best practices for project structure.

        requirements_overview (str): A comprehensive, well-structured document in markdown 
        format that outlines the project's requirements derived from the user's request. 
        This serves as a guide for the development process.

        tasks (list[Task]): A list of Task objects, each encapsulating a distinct unit of work 
        necessary for the project's completion. These tasks are meant to be carried out by the 
        entire team collectively.

        current_task (Task): The Task object currently in focus, representing the active task 
        that team members are working on.

        project_state (Status): An enumerated value reflecting the project's current lifecycle 
        stage, providing real-time tracking of project progress.

        messages (list[tuple[str, str]]): A chronological list of tuples representing the 
        conversation history between the system, user, and AI. Each tuple contains a role 
        identifier (e.g., 'AI', 'tool', 'user', 'system') and the corresponding message.

        is_requirements_written_to_local (bool): A flag indicating if the requirements have been
        written to the local system.
    """

    user_request: Annotated[
        str,
        "The original set of requirements provided by the user, serving as the "
        "foundation for the project."
    ]

    user_requested_standards: Annotated[
        str,
        "The specific standards or protocols the user has requested to be implemented"
        " in the project, which could include coding standards, design patterns, or "
        "industry-specific standards."
    ]

    project_name: Annotated[
        str, 
        "The name of the project."
    ]

    project_folder_strucutre: Annotated[
        str,
        "The organized layout of directories and subdirectories that form the project's "
        "file system, adhering to best practices for project structure."
    ]

    requirements_overview: Annotated[
        str, 
        "A comprehensive, well-structured document in markdown format that outlines "
        "the project's requirements derived from the user's request. This serves as a "
        "guide for the development process."
    ]

    tasks: Annotated[
        list[Task],
        "A list of Task objects, each encapsulating a distinct unit of work necessary "
        "for the project's completion. These tasks are meant to be carried out by the "
        "entire team collectively."
    ]

    current_task: Annotated[
        Task,
        "The Task object currently in focus, representing the active task that team "
        "members are working on."
    ]

    project_state: Annotated[
        Status,
        "An enumerated value reflecting the project's current lifecycle stage, providing "
        "real-time tracking of project progress."
    ]

    messages: Annotated[
        list[tuple[str, str]], 
        "A chronological list of tuples representing the conversation history between the "
        "system, user, and AI. Each tuple contains a role identifier (e.g., 'AI', 'tool', "
        "'user', 'system') and the corresponding message."
    ]
