""" Graph State for PM Agent """
from typing import Annotated, List, TypedDict

from agents.base.base_state import BaseState
from models.coder_models import CodeGenerationPlan
from models.constants import ChatRoles, PStatus
from models.models import (Issue, IssuesQueue, PlannedIssue,
                           PlannedIssuesQueue, PlannedTask, PlannedTaskQueue,
                           RequirementsDocument, Task, TaskQueue)
from models.tests_generator_models import FileFunctionSignatures


class SupervisorState(TypedDict):
    """
    Represents the state of Project Manager to maintain the project level information
    and status.
    """

    # @in
    project_id: Annotated[
        int,
        BaseState.in_field("The ID of the project being generated.")
    ]

    # @out
    project_name: Annotated[
        str,
        BaseState.out_field("The name of the project being generated.")
    ]

    # @out
    project_status: Annotated[
        PStatus,
        BaseState.out_field("The status of the project being generated.")
    ]

    # @out
    agents_status: Annotated[
        str,
        BaseState.out_field("The current status of the agent working on the project.")
    ]

    # @in
    microservice_id: Annotated[
        int, 
        BaseState.in_field("The ID of the microservice being generated.")
    ]

    # @out
    microservice_name: Annotated[
        str,
        BaseState.out_field("The name of the microservice being generated.")
    ]

    # @in
    original_user_input: Annotated[
        str,
        BaseState.in_field("The prompt provided by the user.")
    ]

    # @in
    project_path: Annotated[
        str,
        BaseState.in_field("The path where the project is being written.")
    ]

    # @in
    license_url: Annotated[
        str,
        BaseState.in_field("The license URL for the project, provided by the user.")
    ]

    # @in
    license_text: Annotated[
        str,
        BaseState.in_field("The license text for the codebase.")
    ]

    # @out
    current_task: Annotated[
        Task,
        BaseState.out_field("The current task that the team is working on.")
    ]

    # @out
    current_planned_task: Annotated[
        PlannedTask,
        BaseState.out_field("The current planned task that the team is working on.")
    ]

    # @out
    current_issue: Annotated[
        Issue,
        BaseState.out_field("The issue that is currently being worked on.")
    ]

    # @out
    current_planned_issue: Annotated[
        PlannedIssue,
        BaseState.out_field("The planned issue that the team is currently addressing.")
    ]

    # @out
    is_rag_query_answered: Annotated[
        bool,
        BaseState.out_field("Indicates whether the RAG agent has answered the query.")
    ]

    # @out
    rag_cache_queries: Annotated[
        List[str],
        BaseState.out_field("Queries generated for the RAG cache.")
    ]

    # @out
    issues: Annotated[
        IssuesQueue,
        BaseState.out_field("A queue of issues created by the reviewer.")
    ]

    # @out
    tasks: Annotated[
        TaskQueue, 
        BaseState.out_field("Tasks created during project generation.")
    ]

    # @inout
    messages: Annotated[
        List[tuple[ChatRoles, str]], 
        BaseState.inout_field(
            "A chronological list of tuples representing the conversation history"
            "between the system, user, and AI. Each tuple contains a role identifier"
            " (e.g., 'AI', 'tool', 'user', 'system') and the corresponding message."
        )
    ]

    # @out
    human_feedback: Annotated[
        List[tuple[str, str]], 
        BaseState.inout_field(
            "A list of human inputs provided during the human-in-the-loop process."
        )
    ]

    # @in
    functions_skeleton: Annotated[
        FileFunctionSignatures,
        BaseState.in_field(
            "The detailed function skeletons for the functions in the code."
        )
    ]

    # @in
    test_code: Annotated[
        str, 
        BaseState.in_field(
            "The complete, well-documented unit test code that adheres to all requested"
            "standards for the specified programming language and framework."
        )
    ]

    # @out
    planned_tasks: Annotated[
        PlannedTaskQueue,  # This is a list of work packages created by the planner.
        BaseState.out_field("A list of work packages planned by the planner.")
    ]

    # @out
    planned_issues: Annotated[
        PlannedIssuesQueue,  # This is a list of work packages created by the planner.
        BaseState.out_field("A list of planned issues.")
    ]

    # @out
    rag_retrieval: Annotated[
        str,
        BaseState.out_field("The RAG retrieved data.")
    ]

    # @out
    requirements_document: Annotated[
        RequirementsDocument,
        BaseState.inout_field(
            "A comprehensive, well-structured document in Markdown format outlining "
            "the project's requirements derived from the user's request. This serves "
            " as a guide for the development process."
        )
    ]

    # @out
    code_generation_plan_list: Annotated[
        List[CodeGenerationPlan],
        BaseState.out_field("A list of code generation plans.")
    ]

    # @internal
    previous_project_status: Annotated[
        PStatus,
        BaseState.internal_field("The status of the previous project.")
    ]

    # @internal
    rag_cache_building: Annotated[
        str,
        BaseState.internal_field(
            "Holds the questions and answers related to the cache building queries."
        )
    ]

    # @internal
    is_rag_cache_created: Annotated[
        bool,
        BaseState.internal_field(
            "Indicates whether the RAG cache has been created. This is a "
            "single-time update."
        )
    ]

    # @internal
    is_initial_additional_info_ready: Annotated[
        bool,
        BaseState.internal_field(
            "Indicates whether the initial additional information is ready. "
            "This is set once."
        )
    ]

    # @internal
    are_requirements_prepared: Annotated[
        bool,
        BaseState.internal_field(
            "Indicates whether the requirements have been prepared. "
            "This is a single-time update."
        )
    ]

    # @internal
    are_planned_tasks_in_progress: Annotated[
        bool,
        BaseState.internal_field(
            "Indicates whether any planned tasks are currently in progress. "
            "This flag is managed by the supervisor:\n"
            "- Set to True when the planner breaks down larger tasks into smaller planned tasks.\n"
            "- Set to False when the planned tasks list is empty.\n"
            "The flag is used to control a loop that operates while planned tasks are being created and processed."
        )
    ]

    # @internal
    are_planned_issues_in_progress: Annotated[
        bool,
        BaseState.internal_field(
            "Indicates whether any planned issues are currently in progress. "
            "This flag is managed by the supervisor:\n"
            "- Set to True when the planner breaks down larger issues into smaller planned issues.\n"
            "- Set to False when the planned issues list is empty.\n"
            "The flag is used to control a loop that operates while planned issues are being created and processed."
        )
    ]

    # @internal
    is_human_reviewed: Annotated[
        bool,
        BaseState.internal_field(
            "Indicates whether the human review has been completed."
        )
    ]
