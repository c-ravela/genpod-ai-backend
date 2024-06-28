""" Graph State for PM Agent """
from typing import List, Tuple, Annotated
import operator
from typing_extensions import TypedDict
from models.models import Task

class SupervisorState(TypedDict):
    """
    Represents the state of Project Manager to maintain the project level information and status.

    Attributes:
        original_user_input: User assigned task
        team_members: List of agents workflows that the Project Manager can invoke
        rag_retrieval: Whenever an agent needs any additional information a RAG Workflow is triggered to retrieve that information
        tasks: List of deliverables that needs to be completed to mark the project as complete
        current_task: Current task any agent is currently working on
        agents_status: What is the status of the agent that is currently working on the project
        messages: List of messages between Project Manager and other agents
    """

    original_user_input: str
    project_path: str
    team_members: dict
    rag_retrieval: str
    tasks: List[str]
    current_task: Task
    agents_status: str
    messages: List[Tuple[str, str]]
    rag_query_answer = bool

def add_message(state: SupervisorState, message: tuple[str, str]) -> SupervisorState:
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
    return {**state}