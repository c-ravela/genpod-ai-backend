"""Coder State

Agent graph state
"""

from models.models import Task

from typing_extensions import TypedDict
from typing_extensions import Annotated
from models.skeleton import FunctionSkeleton

class CoderState(TypedDict):
    """
    """

    # @in 
    project_name: Annotated[
        str, 
        "The name of the project."
    ]

    # @in 
    project_folder_strucutre: Annotated[
        str,
        "The organized layout of directories and subdirectories that form the project's "
        "file system, adhering to best practices for project structure."
    ]

    # @in 
    requirements_overview: Annotated[
        str, 
        "A comprehensive, well-structured document in markdown format that outlines "
        "the project's requirements derived from the user's request. This serves as a "
        "guide for the development process."
    ]

    # @in
    generated_project_path: Annotated[
        str,
        "The absolute path in the file system where the project is being generated. "
        "This path is used to store all the project-related files and directories."
    ]

    # @in
    license_url: Annotated[
        str,
        ""
    ]

    # @in
    license_text: Annotated[str, ""]

    # @in
    functions_skeleton:Annotated[
        FunctionSkeleton,
        """The well detailed function skeleton for the functions that are in the code."""
        ]

    # @in
    test_code: Annotated[
        str, 
        "The complete, well-documented working unit test code that adheres to all standards "
        "requested with the programming language, framework user requested ",
    ]

    # @inout
    current_task: Annotated[
        Task,
        "The Task object currently in focus, representing the active task that team "
        "members are working on."
    ]
    
    # @inout
    messages: Annotated[
        list[tuple[str, str]], 
        "A chronological list of tuples representing the conversation history between the "
        "system, user, and AI. Each tuple contains a role identifier (e.g., 'AI', 'tool', "
        "'user', 'system') and the corresponding message."
    ]

    # @out
    code: Annotated[
        str, 
        "The complete, well-documented working code that adheres to all standards "
        "requested with the programming language, framework user requested ",
    ]

    # @out
    files_created: Annotated[
        list[str], 
        "The absolute paths of file that were created for this project "
        "so far."
    ]

    # @out
    infile_license_comments: Annotated[
        dict[str, str],
        "A list of multiline license comments for each type of file."
    ]

    commands_to_execute: Annotated[ 
        dict[str, str],
        """
        This field represents a dictionary of commands intended to be executed on a Linux terminal. Each key-value pair in the dictionary corresponds to an absolute path (the key) and a specific command (the value) to be executed at that path.
        """
    ]