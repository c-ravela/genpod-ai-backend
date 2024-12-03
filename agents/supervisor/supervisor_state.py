""" Graph State for PM Agent """
from typing import List

from typing_extensions import Annotated, TypedDict

from agents.agent.state import State
from models.coder_models import CodeGenerationPlan
from models.constants import ChatRoles, PStatus
from models.models import (Issue, IssuesQueue, PlannedIssue,
                           PlannedIssuesQueue, PlannedTask, PlannedTaskQueue,
                           RequirementsDocument, Task, TaskQueue)
from models.tests_generator_models import FileFunctionSignatures


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
        PStatus,
        State.out_field("The status of the project being generated.")
    ]

    # @out
    agents_status: Annotated[
        str,
        State.out_field()
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
    current_task: Annotated[
        Task,
        State.out_field("The current task that team is working on.")
    ]

    # @out
    current_planned_task: Annotated[
        PlannedTask,
        State.out_field("The current planned task that team is working on.")
    ]

    # @out
    current_issue: Annotated[
        Issue,
        State.out_field("This field represents the issue that is currently being worked on.")
    ]

    # @out
    current_planned_issue: Annotated[
        PlannedIssue,
        State.out_field("The current planned issue that team is working on.")
    ]

    # @out
    is_rag_query_answered : Annotated[
        bool,
        State.out_field("is query answered by rag agent.")
    ]

    # @out
    rag_cache_queries: Annotated[
        List[str],
        State.out_field("Queries generated for rag cache")
    ]

    # @out
    issues: Annotated[
        IssuesQueue,
        State.out_field("A queue of issues that have been created by the reviewer.")
    ]

    # @out
    tasks: Annotated[
        TaskQueue, 
        State.out_field("The tasks create while generating the project.")
    ]

    # @inout
    messages: Annotated[
        list[tuple[ChatRoles, str]], 
        State.inout_field(
            "A chronological list of tuples representing the conversation history between the "
            "system, user, and AI. Each tuple contains a role identifier (e.g., 'AI', 'tool', "
            "'user', 'system') and the corresponding message."
        )
    ]

    # @out
    human_feedback: Annotated[
        list[tuple[str, str]], 
        State.inout_field(
            "A list human inputs given during human in the loop process"
        )
    ]

    # @in
    functions_skeleton: Annotated[
        FileFunctionSignatures,
        State.in_field(
            "The well detailed function skeleton for the functions that are in the code."
        )
    ]

    # @in
    test_code: Annotated[
        str, 
        State.in_field(
            "The complete, well-documented working unit test code that adheres to all standards "
            "requested with the programming language, framework user requested "
        )
    ]

    # @out
    planned_tasks: Annotated[
        PlannedTaskQueue, # This is list of work_packages created by the planner,
        State.out_field("A list of work packages planned by the planner")
    ]

    # @out
    planned_issues: Annotated[
        PlannedIssuesQueue, # This is list of work_packages created by the planner,
        State.out_field("A list of planned issues")
    ]

    # @out
    rag_retrieval: Annotated[
        str,
        State.out_field()
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

    # @out
    code_generation_plan_list: Annotated[
        List[CodeGenerationPlan],
        State.out_field()
    ]

    # external
    previous_project_status: Annotated[
        PStatus,
        ''
    ]

    # external
    rag_cache_building: Annotated[
        str,
        ''
    ]

    is_rag_cache_created: Annotated[
        bool,
        'Represents whether rag cache was created or not. single time update'
    ]

    is_initial_additional_info_ready: Annotated[
        bool,
        'single time update. set once'
    ]

    are_requirements_prepared: Annotated[
        bool,
        'single time update'
    ]

    are_planned_tasks_in_progress: Annotated[
        bool,
        """
        Indicates whether any planned tasks are currently in progress.
        This flag is managed by the supervisor:
         - Set to True when the planner breaks down larger tasks into smaller
           planned tasks.
         - Set to False when the planned tasks list is empty.
        The flag is used to control a loop that operates while planned tasks
        are being created and processed.
        """
    ]

    are_planned_issues_in_progress: Annotated[
        bool,
        """
        Indicates whether any planned issues are currently in progress.
        This flag is managed by the supervisor:
        - Set to True when the planner breaks down larger issues into smaller
          planned issues.
        - Set to False when the planned issues list is empty.
        The flag is used to control a loop that operates while planned issues
        are being created and processed.
        """
    ]

    is_human_reviewed: Annotated[bool, '']

def add_message(state: SupervisorState, message: tuple[ChatRoles, str]) -> SupervisorState:
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
