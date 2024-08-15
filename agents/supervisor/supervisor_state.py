""" Graph State for PM Agent """
from typing import List, Tuple

from typing_extensions import Annotated, TypedDict

from models.models import Task
from agents.agent.state import State

from models.models import RequirementsDocument

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

    # @in
    project_id: Annotated[
        int,
        State.in_field("The id of the project being generated.")
    ]

    # @out
    project_name: Annotated[
        str,
        State.out_field("The name of the project being generated.")
    ]

    # @out
    project_status: Annotated[
        str,
        State.out_field("The status of the project being generated.")
    ]

    # @in
    microservice_id: Annotated[
        int, 
        State.in_field("The id of the microservice being generated.")
    ]

    # @out
    microservice_name: Annotated[
        str,
        State.out_field("The name of the microservice being generated.")
    ]

    # @in
    original_user_input: Annotated[
        str,
        State.in_field("The prompt given by user.")
    ]

    # @in
    project_path: Annotated[
        str,
        State.in_field("The path of the project where its being written.")
    ]

    # @in
    license_url: Annotated[
        str,
        State.in_field("The license url to the project, given by the user.")
    ]

    # @in
    license_text: Annotated[
        str,
        State.in_field("The license text for code base.")
    ]

    # @out
    tasks: Annotated[
        List[Task], 
        State.out_field("The tasks create while generating the project.")
    ]

    # @out
    current_task: Annotated[
        List[Task],
        State.out_field("The current task that is team is working on.")
    ]

    # @out
    team_members: Annotated[
        dict,
        State.out_field("map of team members")
    ]

    # @out
    requirements_document: Annotated[
        RequirementsDocument,
        State.inout_field(
            "A comprehensive, well-structured document in markdown format that outlines "
            "the project's requirements derived from the user's request. This serves as a "
            "guide for the development process."
        )
    ]

    # @inout
    messages: Annotated[
        list[tuple[str, str]], 
        State.inout_field(
            "A chronological list of tuples representing the conversation history between the "
            "system, user, and AI. Each tuple contains a role identifier (e.g., 'AI', 'tool', "
            "'user', 'system') and the corresponding message."
        )
    ]

    # @out
    human_feedback:  Annotated[
        list[tuple[str, str]], 
        State.inout_field(
            "A list human inputs given during human in the loop process"
        )
    ]

    # @out
    rag_cache_queries: Annotated[
        List[str],
        State.out_field("Queries generated for rag cache")
    ]

    # @out
    rag_query_answer : Annotated[
        bool,
        State.out_field("is query answered by rag agent.")
    ]

    rag_retrieval: str

    planned_tasks: List[Task] # This is list of work_packages created by the planner
    planned_task_map: dict # This is the a map of deliverables to work_packages
    planned_task_requirements: dict # This is the map of work_packages to json formatted requirements
    agents_status: str

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