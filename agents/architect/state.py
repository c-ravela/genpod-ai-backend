"""
Architect Agent

graph state
"""

from typing_extensions import TypedDict

from agents.architect.model import TaskInfo

class ArchitectState(TypedDict): 
    """
    """

    error: str
    tasks: list[TaskInfo]
    project_folders: list[str]
    current_task: TaskInfo
    project_state: str
    messages: list[str]

def toggle_error(state: ArchitectState) -> ArchitectState:
    """
    toggle error field. true -> false and flase -> true

    Ex: state = toggle_error(state)
    """

    state['error'] = not state['error']
    
    return state

def add_message(state: ArchitectState, message: tuple[str, str]) -> ArchitectState:
    """
    Adds a single message to the the messages

    message: tuple[str, str]

    Ex: state = add_message(state, ('user', 'single message'))
    """

    state['messages'] += [message]
    return state
