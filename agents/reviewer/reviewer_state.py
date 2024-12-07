"""
"""

from typing_extensions import Annotated, TypedDict

from agents.base.base_state import BaseState
from models.models import IssuesQueue


class ReviewerState(TypedDict):
    """
    """

    # @in 
    project_name: Annotated[
        str, 
        BaseState.in_field(
            "The name of the project."
        )
    ]

    # @in
    project_path: Annotated[
        str,
        BaseState.in_field(
            "The absolute path in the file system where the project is being generated. "
            "This path is used to store all the project-related files and directories."
        )
    ]

    # @in
    license_text: Annotated[
        str,
        BaseState.in_field("The license text for code base.")
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
        BaseState.in_field(
            "Issues identified in the generated project during reviewing phase."
        )
    ]
