""" Graph State for PM Agent """
from typing import List
from typing_extensions import TypedDict
from .supervisor_models import TaskDetails

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
    team_members: dict
    rag_retrieval: str
    tasks: List[str]
    current_task: TaskDetails
    agents_status: str
    messages: List[str]