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
    message: list[tuple[str, str]]

    def toggle_error(self) -> None:
        self.state['error'] = not self.state['error']

    def add_message(self, message: tuple[str, str]) -> None:

        self.state['messages'] += [message]