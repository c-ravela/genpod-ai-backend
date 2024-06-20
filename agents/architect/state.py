"""Architect State

This module contains the ArchitectState class which is a TypedDict representing 
the state of the Architect agent. It also includes functions to manipulate the 
state.
"""

from typing_extensions import TypedDict

from models.models import Task

class ArchitectState(TypedDict): 
    """
    ArchitectState Class

    This class represents the state of the Architect agent. It includes fields 
    for error status, tasks, project folders, current task, project state, and 
    messages. Each field has a specific type and role in maintaining the state 
    of the agent.
    """

    error: str
    tasks: list[Task]
    project_folders: list[str]
    current_task: Task
    project_state: str
    messages: list[str]

def toggle_error(state: ArchitectState) -> ArchitectState:
    """
    Toggles the error field in the state. If the error is True, it becomes 
    False and vice versa.

    Args:
        state (ArchitectState): The current state of the Architect agent.

    Returns:
        ArchitectState: The updated state with the toggled error field.
    """

    state['error'] = not state['error']
    
    return state

def add_message(state: ArchitectState, message: tuple[str, str]) -> ArchitectState:
    """
    Adds a single message to the messages field in the state.

    Args:
        state (ArchitectState): The current state of the Architect agent.
        message (tuple[str, str]): The message to be added.

    Returns:
        ArchitectState: The updated state with the new message added to the 
        messages field.
    """

    state['messages'] += [message]
    return state
