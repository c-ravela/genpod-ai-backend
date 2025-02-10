"""
ReviewerState

Defines the state structure for the ReviewerAgent, including project details,
requirements, and identified issues.
"""

from typing import Annotated, TypedDict

from agents.base.base_state import BaseState
from models.models import IssuesQueue


class ReviewerState(TypedDict):
    """
    Represents the state for the ReviewerAgent, encapsulating project details,
    requirements, and identified issues.

    Attributes:
        project_name (str): Name of the project under review.
        project_path (str): Absolute path where the project is stored.
        license_text (str): License information associated with the project.
        requirements_document (str): Requirements in markdown format serving as
            a guide for the review process.
        issues (IssuesQueue): A queue of issues identified during the review phase.
        error_message (str): An internal field to store any error messages
            encountered during the review process.
    """

    # @in 
    project_name: Annotated[
        str, 
        BaseState.in_field(
            "The name of the project under review."
        )
    ]

    # @in
    project_path: Annotated[
        str,
        BaseState.in_field(
            "The absolute path in the file system where the project is being generated. "
            "This path is used to store all project-related files and directories."
        )
    ]

    # @in
    license_text: Annotated[
        str,
        BaseState.in_field(
            "The license text associated with the project."
        )
    ]

    # @in 
    requirements_document: Annotated[
        str, 
        BaseState.in_field(
            "A comprehensive, well-structured document in markdown format that outlines "
            "the project's requirements derived from the user's request. This serves as a "
            "guide for the development process."
        )
    ]
    
    # @out
    issues: Annotated[
        IssuesQueue,
        BaseState.out_field(
            "A queue of issues identified in the project during the review phase."
        )
    ]

    # @internal
    error_message: Annotated[
        str,
        BaseState.internal_field(
            "Stores error messages encountered during the review process for debugging and logging purposes."
        )
    ]
