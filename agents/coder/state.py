"""Coder State

Agent graph state
"""

from models.models import Task

from typing import TypedDict


class CoderState(TypedDict):
    """
    """

    error: str
    current_task: Task
    current_step: Task
    steps: list[Task]
    requirements_overview: str
    project_folder_structure: str
    message: list[tuple[str, str]]
