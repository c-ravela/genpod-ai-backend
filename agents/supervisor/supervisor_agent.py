import ast
import os
from typing import TYPE_CHECKING, Dict, List, Tuple

from langchain_core.messages import AIMessage
from pydantic import ValidationError

from agents.agent.agent import Agent
from agents.supervisor.supervisor_state import SupervisorState
from llms.llm import LLM
from models.constants import ChatRoles, PStatus, Status
from models.models import (Issue, IssuesQueue, PlannedIssue,
                           PlannedIssuesQueue, PlannedTask, PlannedTaskQueue,
                           RequirementsDocument, Task, TaskQueue)
from models.supervisor_models import QueryList
from prompts.supervisor_prompts import SupervisorPrompts
from utils.fuzzy_rag_cache import FuzzyRAGCache
from utils.logs.logging_utils import logger

# to avoid circular dependency
if TYPE_CHECKING:
    from genpod.team import TeamMembers  # Adjust import path as needed


class SupervisorAgent(Agent[SupervisorState, SupervisorPrompts]):

    team: 'TeamMembers'
    previous_project_status: PStatus

    def __init__(self, agent_id: str, agent_name: str, llm: LLM) -> None:

        super().__init__(
            agent_id,
            agent_name,
            SupervisorState(),
            SupervisorPrompts(),
            llm
        )
        self.team = None
        self.previous_project_status = PStatus.NONE

        # TODO - LOW: has to be moved to RAG agent
        self.rag_cache = FuzzyRAGCache()
        self.rag_cache_building = ''

        # TODO - LOW: has to be moved to RAG agent
        self.is_rag_cache_created: bool = False  # Represents whether rag cache was created or not. single time update
      
        self.is_initial_additional_info_ready: bool = False  # single time update. set once
        self.are_requirements_prepared: bool = False  # single time update

        # Indicates whether any planned tasks are currently in progress.
        # This flag is managed by the supervisor:
        # - Set to True when the planner breaks down larger tasks into smaller 
        #   planned tasks.
        # - Set to False when the planned tasks list is empty.
        # The flag is used to control a loop that operates while planned tasks 
        # are being created and processed.
        self.are_planned_tasks_in_progress: bool = False

        # Indicates whether any planned issues are currently in progress.
        # This flag is managed by the supervisor:
        # - Set to True when the planner breaks down larger issues into smaller 
        #   planned issues.
        # - Set to False when the planned issues list is empty.
        # The flag is used to control a loop that operates while planned issues 
        # are being created and processed.
        self.are_planned_issues_in_progress: bool = False

        self.calling_agent: str = ""
        self.called_agent: str = ""

        self.is_human_reviewed: bool = False

        self.responses: Dict[str, List[Tuple[str, Task]]] = {}
        self.tasks = []

    def setup_team(self, team: 'TeamMembers') -> None:
        """
        Sets up the team for the project.

        This method assigns the provided team object to the instance's team attribute.

        Args:
            team (TeamMembers): An instance of the TeamMembers class, which represents
                                the team to be assigned.

        Returns:
            None: This method does not return any value.
        """

        self.team = team

    # TODO - LOW: has to be moved to RAG agent
    def build_rag_cache(self, query: str) -> tuple[list[str], str]:
        """
        takes the user requirements as an input and prepares a set of queries
        (anticipates the questions) that team members might get back with and 
        prepares the answers for them and hold them in the rag cache.

        returns list of queries and response to the queries.
        """
        # I need to build a rag_cache during kick_off with answers to questions 
        # about requirements.
        context = ''
        count = 3

        validated_requirements_queries = QueryList(req_queries=[])

        # Prepare questionaire for rag cache
        while count > 0:
            try:
                response = self.llm.invoke(
                    self.prompts.init_rag_questionaire_prompt, 
                    {
                        'user_prompt': query,
                        'context': context
                    }
                )
                req_queries: AIMessage = response.response
                req_queries = ast.literal_eval(req_queries.content)
                validated_requirements_queries = QueryList(req_queries=req_queries)
                break
            except (ValidationError, ValueError, SyntaxError) as e:
                context += str(e)
                count = count-1

        if len(validated_requirements_queries.req_queries) > 0:
            final_response = ''

            for req_query in validated_requirements_queries.req_queries:
                result = self.rag_cache.get(req_query)

                if result is not None:
                    logger.debug("Cache hit for query: %s", req_query)
                    rag_response = result
                else:
                    logger.debug("Cache miss for query: %s", req_query)
                    logger.info(f'{self.team.rag.member_name} Agent Called to Query')
                    logger.info("Query: %s", req_query)

                    result = self.team.rag.invoke({
                        'question': req_query,
                        'max_hallucination': 3
                    })

                    rag_response = result['generation']
                    self.rag_cache.add(req_query, rag_response)

                    logger.info(f"{self.team.rag.member_name} Agent Response")
                    logger.info(f"{self.team.rag.member_name} Response: %s", rag_response)

                    if result['query_answered'] is True:
                        # Evaluate the RAG response
                        llm_output = self.llm.invoke(
                            self.prompts.follow_up_questions, 
                            {
                                'user_query': req_query,
                                'initial_rag_response': rag_response
                            }
                        )

                        evaluation_result: AIMessage = llm_output.response
                        if evaluation_result.content.startswith("COMPLETE"):
                            final_response += (
                                f"Question: {req_query}\nAnswer: "
                                f"{rag_response}\n\n"
                            )
                        elif evaluation_result.content.startswith("INCOMPLETE"):
                            follow_up_query = evaluation_result.content.split(
                                "Follow-up Query:"
                            )[1].strip()

                            logger.info("----------Follow-up query needed----------")
                            logger.info("Follow-up: %s", follow_up_query)

                            # Ask the follow-up query to the RAG agent
                            follow_up_result = self.team.rag.invoke({
                                'question': follow_up_query,
                                'max_hallucination': 3
                            })

                            follow_up_response = follow_up_result['generation']
                            self.rag_cache.add(follow_up_query, follow_up_response)

                            final_response += (
                                f"Question: {req_query}\nInitial Answer: {rag_response}\n"
                                f"Follow-up Question: {follow_up_query}\n"
                                f"Follow-up Answer: {follow_up_response}\n\n"
                            )
                        else:
                            logger.info("Unexpected evaluation result format")

                            final_response += (
                                f"Question: {req_query}\nAnswer: {rag_response}\n\n"
                            )

            return (validated_requirements_queries.req_queries, final_response)

        return ([], 'Failed to initialize project')

    def instantiate_state(self, state: SupervisorState) -> SupervisorState:
        """
        Initializes the state for the supervisor agent.

        This method sets up the initial state for the supervisor agent, ensuring all necessary
        attributes are initialized. It also checks if the team has been set up before proceeding.

        Args:
            state (SupervisorState): The state object to be initialized.

        Returns:
            SupervisorState: The initialized state object.

        Raises:
            ValueError: If the team has not been initialized.
        """

        if self.team is None:
            raise ValueError(
                f"Error: The team for '{self.agent_name}' has not been initialized. "
                f"Current value of 'self.team': {self.team}. "
                "Please ensure that the 'set_team' method has been called on the supervisor agent "
                "to initialize the team before attempting this operation."
            )

        # initialize supervisor state
        state['project_name'] = ""
        state['project_status'] = PStatus.RECEIVED
        state['agents_status'] = ''
        state['microservice_name'] = ""
        state['current_task'] = Task()
        state['current_planned_task'] = PlannedTask()
        state['current_planned_issue'] = PlannedIssue(is_function_generation_required=False)
        state['current_issue'] = Issue()
        state['is_rag_query_answered'] = False
        state['rag_cache_queries'] = []
        state['issues'] = IssuesQueue()
        state['tasks'] = TaskQueue()
        state['messages'] = [
            (
                ChatRoles.USER,
                state['original_user_input']
            ),
            (
                ChatRoles.SYSTEM, 
                f'A new project with the following details has been received from the user: {state["original_user_input"]}'
            )
        ]
        state['human_feedback'] = []
        state['functions_skeleton'] = {}
        state['test_code'] = ""
        state['planned_tasks'] = PlannedTaskQueue()
        state['planned_issues'] = PlannedIssuesQueue()
        state['rag_retrieval'] = ''
        state['requirements_document'] = RequirementsDocument()
        state['code_generation_plan_list'] = []

        self.responses = {member.member_id: [] for member in self.team.get_team_members_as_list()}
       
        logger.info(f"Supervisor state has been initialized successfully. current supervisor state: {state}")
       
        return state

    def call_rag(self, state: SupervisorState) -> SupervisorState:
        """
            Gathers the required information from vector DB.
        """

        logger.info(f"{self.team.rag.member_name} has been called.")
        self.called_agent = self.team.rag.member_id

        # TODO - LOW: RAG cache creation has to be moved to RAG agent
        # check if rag cache was ready if not prepare one
        if not self.is_rag_cache_created:
            logger.info(f"{self.team.rag.member_name}: creating the RAG cache.")

            # TODO - MEDIUM: Define a proper data structure for holding the RAG queries 
            # and answers together.
            # Reason: self.rag_cache_building is a string that holds all the queries 
            # and answers. When a cache hit occurs, we use self.rag_cache_building as 
            # a response. This can provide too much information, which might be 
            # unnecessary at that moment or might include irrelevant information.
            # SIDE EFFECTS:
            # 1. LLMs might hallucinate.
            # 2. Increases the usage of prompt tokens.

            # TODO - MEDIUM: Set a cache size limit.
            # Potential issue: As the cache grows, performance issues may arise, 
            # significantly slowing down the application since we are dealing with 
            # strings and performing many string comparisons.
            # Solution: Choose and implement algorithms like LRU (Least Recently Used) 
            # or LFU (Least Frequently Used).
            state['rag_cache_queries'], self.rag_cache_building = self.build_rag_cache(
                state['original_user_input']
            )

            self.is_rag_cache_created = True
            logger.info(
                f"{self.team.rag.member_name}: The RAG cache has been created."
                f"The following queries were used during the process: {state['rag_cache_queries']}"
            )

        question = state['current_task'].question
        try:

            # Check RAG cache for the information first
            result = self.rag_cache.get(question)
            if result is not None:
                logger.debug("Cache hit for query: \n%s", question)

                state['is_rag_query_answered'] = True
            else:
                logger.debug("Cache miss for query: \n%s", question)

                additional_info = self.team.rag.invoke({
                    'question': question,
                    'max_hallucination': 3
                })

                result = additional_info['generation']
                state['is_rag_query_answered'] = additional_info['query_answered']
                self.rag_cache.add(question, result)

            logger.info(
                f"{self.team.rag.member_name} is ready with a response for the query: {question}"
            )
        except Exception as e:
            raise e

        if state['project_status'] == PStatus.NEW:
            if state['current_task'].task_status == Status.NEW:
                logger.info(
                    f"{self.team.rag.member_name}: Received user requirements and "
                    "gathering additional information."
                )
                state['messages'] += [
                    (
                        ChatRoles.AI,
                        f"{self.team.rag.member_name}: Received user requirements and"
                        " gathering additional information."
                    )
                ]

                state['current_task'].additional_info = f"{result}\n{self.rag_cache_building}"
                state['current_task'].task_status = Status.DONE
                self.is_initial_additional_info_ready = True
                state['rag_retrieval'] = result + "\n" + self.rag_cache_building
                state['agents_status'] = f'{self.team.rag.member_name} completed'
                self.responses[self.team.rag.member_id].append(
                    ("Returned from RAG database", state['current_task'])
                )

                return state
        elif state['project_status'] == PStatus.MONITORING:
            if state['current_task'].task_status == Status.AWAITING:
                logger.info(
                    f"{self.team.rag.member_name}: Received a query from team members"
                    " and preparing an answer."
                )
                state['messages'] += [
                    (
                        ChatRoles.AI,
                        f"{self.team.rag.member_name}: Received a query from team "
                        "members and preparing an answer."
                    )
                ]

                # TODO - MEDIUM: We are adding strings like `RAG_Response:` and using 
                # this word for conditional checks in a few places.
                # problem is performance degradation: the application slows down because 
                # we are searching for a small string in a very large
                # string. 06/09/2024 - conditional checks were removed, but still might 
                # need to reconsider the way we store info.
                state['current_task'].task_status = Status.RESPONDED
                state['current_task'].additional_info += "\nRAG_Response:\n" + result
                state['rag_retrieval'] += result
                state['agents_status'] = f'{self.team.rag.member_name} completed'
                self.responses[self.team.rag.member_id].append(
                    ("Returned from RAG database serving a query", state['current_task'])
                )
                
            return state

        return state

    def call_architect(self, state: SupervisorState) -> SupervisorState:
        """
        Prepares requirements document and answers queries for the team members.
        """

        logger.info(f"{self.team.architect.member_name} has been called.")
        self.called_agent = self.team.architect.member_id

        if state['project_status'] == PStatus.INITIAL:
            logger.info(f"{self.team.architect.member_name}: Started  working on requirements document.")

            architect_result = self.team.architect.invoke({
                'current_task': state['current_task'],
                'project_status': state['project_status'],
                'original_user_input': state['original_user_input'],
                'project_path': state['project_path'],
                'user_requested_standards': state['current_task'].additional_info,
                'license_text': state['license_text'],
                'messages': []
            })

            # if the task_status is done that mean architect has generated all the 
            # required information for team
            if architect_result['current_task'].task_status == Status.DONE:
                self.are_requirements_prepared = True
                state['current_task'] = architect_result['current_task']
                state['agents_status'] = f'{self.team.architect.member_name} completed'
                self.responses[self.team.architect.member_id].append(("Returned from Architect", architect_result['tasks']))
                state['tasks'].extend(architect_result['tasks'])
                state['requirements_document'] = architect_result['requirements_document']
                state['project_name'] = architect_result['project_name']
                state['microservice_name'] = architect_result['project_name']

            elif architect_result['current_task'].task_status == Status.AWAITING: 
                state['current_task'] = architect_result['current_task']
                state['agents_status'] = f'{self.team.architect.member_name} Awaiting'
                self.responses[self.team.architect.member_id].append(
                    ("Returned from Architect with a question:", architect_result['current_task'].question)
                )

            return state
        
        if state['project_status'] == PStatus.MONITORING:
            # Need to query Architect to get additional information for another agent
            # which will be present in called agent and that will never be updated when
            # returning
            logger.info("----------Querying Architect----------")

            architect_result = self.team.architect.invoke({
                'current_task': state['current_task'],
                'project_status': state['project_status'],
                'original_user_input': state['original_user_input'],
                'project_path': state['project_path'],
                'user_requested_standards': state['current_task'].additional_info,
                'license_text': state['license_text'],
                'messages': []
            })

            logger.info("----------Response from Architect Agent----------")
            logger.info("Architect Response: %r", architect_result['current_task'])

            # TODO: make architect to update the task_status to RESPONDED when done. 
            # else keep it awaiting meaning architect has no answer for the question.
            if architect_result['query_answered'] is True:
                state['agents_status'] = f'{self.team.architect.member_name} completed'
                self.responses[self.team.architect.member_id].append(
                    ("Returned from Architect serving a Query", architect_result['current_task'])
                )
                state['current_task'] = architect_result['current_task']

                return state
            
            if state['is_rag_query_answered'] is False and architect_result['query_answered'] is False:
                # Additional Human input is needed
                state['current_task'] = architect_result['current_task']
                state['project_status'] = PStatus.HALTED

        return state

    def call_coder(self, state: SupervisorState) -> SupervisorState:
        """
        """
        state['messages'] += [(
            ChatRoles.AI,
            'Calling Coder Agent'
        )]

        logger.info("---------- Calling Coder ----------")

        coder_result = self.team.coder.invoke({
            'project_status': state['project_status'],
            'project_name': state['project_name'],
            'requirements_document': state['requirements_document'],
            'project_path': state['project_path'],
            'license_url': state['license_url'],
            'license_text': state['license_text'],
            'functions_skeleton': state['functions_skeleton'],
            'test_code': state['test_code'],
            'current_task': state['current_task'],
            'current_planned_task': state['current_planned_task'],
            'current_issue': state['current_issue'],
            'current_planned_issue': state['current_planned_issue'],
            'messages': state['messages']
        })

        if state['project_status'] == PStatus.EXECUTING:
            state['current_planned_task'] = coder_result['current_planned_task']

            if state['current_planned_task'].task_status == Status.DONE:
                logger.info(f"{self.team.coder.member_name} has successfully completed the task. Task ID: {state['current_planned_task'].task_id}.")

                state['code_generation_plan_list'].extend(
                    coder_result['code_generation_plan_list']
                )
                state['agents_status'] = f'{self.team.coder.member_name} has successfully completed the task.'
            elif state['current_planned_task'].task_status == Status.ABANDONED:
                logger.info(f"{self.team.coder.member_name} was unable to complete the task. Abandoned Task ID: {state['current_planned_task'].task_id}.")

                state['agent_status'] = f"{self.team.coder.member_name} has abandoned the task."

            self.called_agent = self.team.coder.member_id
            self.responses[self.team.coder.member_id].append(
                ("Returned from Coder", state['current_planned_task'])
            )
        elif state['project_status'] == PStatus.RESOLVING:
            state['current_planned_issue'] = coder_result['current_planned_issue']

            if state['current_planned_issue'].status == Status.DONE:
                state['code_generation_plan_list'].extend(
                    coder_result['code_generation_plan_list']
                )

        return state

    def call_test_code_generator(self, state: SupervisorState) -> SupervisorState:
        """
        """

        state['messages'] += [(
            ChatRoles.AI,
            'Calling Test Code Generator Agent'
        )]

        logger.info("---------- Calling Test Code Generator ----------")

        test_coder_result = self.team.tests_generator.invoke({
            'project_status': state['project_status'],
            'project_name': state['project_name'],
            'requirements_document': state['requirements_document'],
            'project_path': state['project_path'],
            'current_planned_task': state['current_planned_task'],
            'current_planned_issue': state['current_planned_issue'],
            'messages': []
        })

        if state['project_status'] == PStatus.EXECUTING:
            state['current_planned_task'] = test_coder_result['current_planned_task']

            if state['current_planned_task'].task_status == Status.INPROGRESS:

                # side effect of workaround added in TestGenerator.
                # Doing this for coder.
                state['current_planned_task'].task_status = Status.NEW

                logger.info("Test Code Generator completed work package")
                state['agents_status'] = f'{self.team.tests_generator.member_name} Completed'

                # I feel if these are part of PlannedTask, It makes more sense then to 
                # be in super state because for every coding task these varies.
                state['test_code'] = test_coder_result['test_code']
                state['functions_skeleton'] = test_coder_result['function_signatures']

            elif state['current_planned_task'].task_status == Status.ABANDONED:
                logger.info("Test Coder Generator unable to complete the work package due to : %s", state['current_planned_task'])
                state['agents_status'] = f'{self.team.tests_generator.member_name} Completed With Abandonment'
            else:
                logger.info("Test Coder Generator awaiting for additional information\nCoder Query: %s", state['current_planned_task'])
                state['agents_status'] = f'{self.team.tests_generator.member_name} Generator Awaiting'

            self.called_agent = self.team.tests_generator.member_id
            self.responses[self.team.tests_generator.member_id].append(("Returned from Test Coder Generator", state['current_planned_task']))
        elif state['project_status'] == PStatus.RESOLVING:
            state['current_planned_issue'] = test_coder_result['current_planned_issue']

            if state['current_planned_issue'].status == Status.INPROGRESS:
                state['current_planned_issue'].status = Status.NEW
            elif state['current_planned_issue'].status == Status.ABANDONED:
                state['agent_status'] = f'{self.team.tests_generator.member_id} Completed With Abandonment'

        return state

    def call_supervisor(self, state: SupervisorState) -> SupervisorState:
        """
        Manager of for the team. Makes decisions based on the current state of the
        project.
        """

        logger.info(f"{self.team.supervisor.member_name} has been called.")
        self.called_agent = self.team.supervisor.member_id

        if state['project_status'] == PStatus.RECEIVED:
            # When the project is in the 'RECEIVED' phase:
            # - RAG agent has to be called.
            # - Prepare additional information required by the team for further 
            # processing.

            state['messages'] += [
                (
                    ChatRoles.AI,
                   f"The Genpod team has started working on the project with ID: "
                   f"{state['project_id']} and the following microservice ID: "
                   f"{state['microservice_id']}."
                ),
                (
                    ChatRoles.AI,
                    "A New task has been created for the RAG agent to gather additional"
                    " inforamtion."
                )
            ]

            # create a task for rag agent
            state['current_task'] = Task(
                description='retrieve additional context from RAG system',
                task_status=Status.NEW,
                additional_info='',
                question=state['original_user_input']
            )
            state['project_status'] = PStatus.NEW
            logger.info(f"{self.team.supervisor.member_name}: Created task for RAG agent to gather additional info for the user requested project. Project Status moved to {state['project_status']}")

            return state
        elif state['project_status'] == PStatus.NEW:
            # When the project status is 'NEW':
            # - The RAG Agent task is complete.
            # - The next step is to involve the architect to generate the requirements document for the team.

            # If the task is marked as done, it means the RAG agent has gathered the additional information 
            # needed for the team to begin the project.
            if state['current_task'].task_status == Status.DONE:
                if self.is_initial_additional_info_ready:
                    state['project_status'] = PStatus.INITIAL

                    # create a new task for the architect
                    state['current_task'] = Task(
                        description=self.prompts.architect_call_prompt.format(),
                        task_status=Status.NEW,
                        additional_info=state['rag_retrieval'],
                        question=''
                    )

                    state['messages'] += [
                        (
                            ChatRoles.AI,
                            "RAG agent has gathered the additional information."
                        ),
                        (
                            ChatRoles.AI,
                            "A New task has been created for the Architect agent to gather additional inforamtion."
                        )
                    ]

                    logger.info(f"{self.team.supervisor.member_name}: RAG agent has finished preparing additional information for team members.")
                    logger.info(f"{self.team.supervisor.member_name}: Created new task for architect to work on requirements document. Moved Project to {state['project_status']} phase.")

            self.calling_agent = self.team.supervisor.member_id

            return state
        elif state['project_status'] == PStatus.INITIAL:
            # When the project is in the 'INITIAL' phase:
            # 1. The architect has either completed their tasks or is waiting for 
            # additional information.
            #
            # If the architect has completed their tasks:
            # - Change the project status to 'EXECUTING' and proceed with the next 
            # steps.
            #
            # If the architect is still waiting for additional information:
            # - Change the project status to 'MONITORING' and continue monitoring the 
            # situation.

            # Architect has prepared all the required information.
            if state['current_task'].task_status == Status.DONE:
                if not self.is_human_reviewed:
                    state['project_status'] = PStatus.HALTED

                    logger.info(f"{self.team.supervisor.member_name}: Architect agent has prepared the requirements document for the team.")
                    logger.info(f"{self.team.supervisor.member_name}: Waiting for the human to review the requirements document.")
                else:
                    state['project_status'] = PStatus.EXECUTING
                    state['messages'] += [
                        (
                            ChatRoles.AI,
                            "Architect agent has prepared the requirements document for the team."
                        ),
                        (
                            ChatRoles.AI,
                            "Planner can take initiative and prepare the tasks for the team."
                        )
                    ]

                    logger.info(f"{self.team.supervisor.member_name}: Architect agent has prepared the requirements document for the team.")
                    logger.info(f"{self.team.supervisor.member_name}: Planner can take initiative and prepare the tasks for the team. Moved Project to {state['project_status']} phase.")
            elif state['current_task'].task_status == Status.AWAITING:
                # Architect need additional information to complete the assigned task. 
                # architect provides query in the task packet use it to query RAG.
                self.previous_project_status = state['project_status']
                state['project_status'] = PStatus.MONITORING

                state['messages'] += [
                    (
                        ChatRoles.AI,
                        "Architect agent has requested the additional information."
                    ),
                    (
                        ChatRoles.AI,
                        "RAG Agent will respond to the query."
                    )
                ]

                logger.info(f"{self.team.supervisor.member_name}: Architect agent has requested the additional information.")
                logger.info(f"{self.team.supervisor.member_name}: RAG Agent will respond to the query. Moved Project to {state['project_status']} phase.")
            
            return state
        elif state['project_status'] == PStatus.MONITORING:
            # When the project status is 'MONITORING':
            # - If the current task status is 'RESPONDED':
            #   - Change the project status back to the previous state and proceed 
            # with the next steps.

            if state['current_task'].task_status == Status.RESPONDED:
                state['project_status'] = self.previous_project_status
                self.calling_agent = self.called_agent

                state['messages'] += [
                    (
                        ChatRoles.AI,
                        "Team has responded to the query from team member."
                    )
                ]

                logger.info(f"Query has been answered. Moved Project to {state['project_status']} phase.")

            return state
        elif state['project_status'] == PStatus.EXECUTING:
            # When the project status is 'EXECUTING':
            # - The Planner, Coder, and Tester should work on the tasks that have been 
            # prepared by the architect.
            #
            # If there are no planned tasks:
            # - The Planner needs to prepare new tasks.
            #
            # If there are planned tasks:
            # - The Coder and Tester should work on these tasks.
            #
            # Once all the General Tasks were finised(All of the tasks statuses are DONE) 
            # then project state will be 
            # updated to REVIEWING

            # Three scenario for this block of code to get triggered
            # Architect agent has finished generating the requirements documents and 
            # tasks
            # or
            # Coder and Tester completed their task.
            # or
            # all planned tasks were done.
            # Call Planner to prepare planned tasks.

            try:
                state['tasks'].update_item(state['current_task'])
            except Exception as e:
                logger.error(f"`state['tasks']` received an task which is not in the list. \nException: {e}")

            # If any task is abandoned just move on to new task for now. Already task 
            # status is updated in the task list. Will decide on what to do with abandoned
            # tasks later.
            if state['current_task'].task_status in (Status.DONE, Status.ABANDONED):
                next_task = state['tasks'].get_next_item()

                # All task must have been finished.
                if next_task is None:
                    # TODO: Need to consider the Abandoned Tasks. Before considering 
                    # the Project status as REVIEWING.
                    state['project_status'] = PStatus.REVIEWING
                else:
                    state['current_task'] = next_task
            elif state['current_task'].task_status == Status.AWAITING:
                # Planner needs additional information
                # Architect was responsible for answering the query if not then rag 
                # comes into play.
                self.previous_project_status = state['project_status']
                state['project_status'] = PStatus.MONITORING
                self.calling_agent = self.called_agent
            elif state['current_task'].task_status == Status.INPROGRESS:
                # update the planned_task status in the list
                try:
                    state['planned_tasks'].update_item(state['current_planned_task'])
                except Exception as e:
                    logger.error(f"`state['planned_tasks']` received an task which is not in the list. \nException: {e}")

                if state['current_planned_task'].task_status in (Status.NONE, Status.DONE, Status.ABANDONED):
                    next_planned_task = state['planned_tasks'].get_next_item()

                    if next_planned_task is None:
                        self.are_planned_tasks_in_progress = False
                        state['current_task'].task_status = Status.DONE
                    else:
                        state['current_planned_task'] = next_planned_task
                        self.are_planned_tasks_in_progress = True
                        self.calling_agent = self.team.supervisor.member_id

            return state
        elif state['project_status'] == PStatus.REVIEWING:
            # When the project status is 'REVIEWING
            #
            # Reviewer will review the generated project for code quality, linting,
            # Dependancy packages vulnerabilites, code security vulnerabilities,
            # testing(unit testing, functional testing, Integration testing),
            # cloud deployment files(docker files).
            #
            # If there are problems in any of the scenarios then respective team meber
            # has to finish it. Reviewer will return with issues packets.
            #
            # If everythings good(no issues) then Project State will be updated
            # to DONE.

            if state['issues'].has_pending_items():
                state['project_status'] = PStatus.RESOLVING
            else:
                state['project_status'] = PStatus.DONE

            return state
        elif state['project_status'] == PStatus.RESOLVING:

            try:
                state['issues'].update_item(state['current_issue'])
            except Exception as e:
                logger.error(f"`state['issues']` received an issue which is not in the list. \nException: {e}")

            if state['current_issue'].issue_status in (Status.DONE, Status.NONE, Status.ABANDONED):
                if state['issues'].has_pending_items():
                    state['current_issue'] = state['issues'].get_next_item()
                    self.calling_agent = self.team.supervisor.member_id
                else:
                    state['project_status'] = PStatus.REVIEWING
            elif state['current_issue'].issue_status == Status.INPROGRESS:
                try:
                    state['planned_issues'].update_item(state['current_planned_issue'])
                except Exception as e:
                    logger.error(f"`state['planned_issues']` received an task which is not in the list. \nException: {e}")

                if state['current_planned_issue'].status in (Status.NONE, Status.DONE, Status.ABANDONED):
                    if state['planned_issues'].has_pending_items():
                        state['current_planned_issue'] = state['planned_issues'].get_next_item()
                        self.are_planned_issues_in_progress = True
                        self.calling_agent = self.team.supervisor.member_id
                    else:
                        self.are_planned_issues_in_progress = False
                        state['current_issue'].issue_status = Status.DONE
            return state
        elif state['project_status'] == PStatus.HALTED:
            # When the project status is 'HALTED':
            # - The application requires human intervention to resolve issues and
            #  complete the task.

            if self.is_human_reviewed:
                state['project_status'] = PStatus.INITIAL
                if state['current_task'].task_status == Status.INPROGRESS:
                    self.is_human_reviewed = False
            
            return state
        elif state['project_status'] == PStatus.DONE:
            # When the project status is 'DONE':
            # - All tasks have been completed.
            # - The requested output for the user is ready.

            # TODO: Figure out when this stage occurs and handle the logic
            return state
        else:
            return state

    def call_planner(self, state: SupervisorState) -> SupervisorState:
        """
        """

        logger.info("----------Calling Planner----------")
        planner_result = self.team.planner.invoke({
            'context': (
                f"{state['requirements_document'].to_markdown()}\n"
                f"{state['rag_retrieval']}"
            ),
            'current_task': state['current_task'],
            'project_path': state['project_path'],
            'current_issue': state['current_issue'],
            'project_status': state['project_status']
        })

        if state['project_status'] == PStatus.EXECUTING:
            state['current_task'] = planner_result['current_task']

            # If the status is INPROGRESS, it indicates that the planner has 
            # successfully prepared planned tasks.
            # The task is marked as INPROGRESS rather than DONE because:
            # - The planner has set up the tasks, but they have not yet been executed.
            # - The planned tasks are still pending execution.
            # Once all the planned tasks have been addressed, regardless of their 
            # individual states, the current task status will be updated to DONE 
            # by the supervisor.
            if state['current_task'].task_status == Status.INPROGRESS:
                logger.info(f"{self.team.planner.member_name} has successfully completed preparing the planned tasks for Task ID: {state['current_task'].task_id}.")
                state['planned_tasks'].extend(planner_result['planned_tasks'])

                state['agent_status'] = f"Work packages have been built by {self.team.planner.member_name}."
                self.called_agent = self.team.planner.member_id
                self.responses[self.team.planner.member_id].append(
                    ("Returned from Planner", state['current_task'])
                )
            elif state['current_task'].task_status == Status.ABANDONED:
                logger.info(f"{self.team.planner.member_name} has abandoned the task with Task Id: {state['current_task'].task_id}")

                state['agents_status'] = f"{self.team.planner.member_name} has abandoned Task ID: {state['current_task'].task_id}."
                self.called_agent = self.team.planner.member_id

                self.responses[self.team.planner.member_id].append(("Returned from Planner with an abandoned task.", state['current_task']))
            elif state['current_task'].task_status == Status.AWAITING:
                logger.info(f"{self.team.planner.member_name} is requesting additional information for Task ID: {state['current_task'].task_id}.")

                state['agents_status'] = f"{self.team.planner.member_name} is awaiting additional information for Task ID: {state['current_task'].task_id}."

                self.called_agent = self.team.planner.member_id
                self.responses[self.team.planner.member_id].append(
                    ("Returned from Planner with a question", state['current_task'].question)
                )
        elif state['project_status'] == PStatus.RESOLVING:
            state['current_issue'] = planner_result['current_issue']

            if state['current_issue'].issue_status == Status.INPROGRESS:
                logger.info(f"{self.team.planner.member_name} has successfully completed preparing the planned tasks for Issue ID: {state['current_issue'].issue_id}.")
                state['planned_issues'].extend(planner_result['planned_issues'])

                state['agent_status'] = f"Planned issues have been prepared by {self.team.planner.member_name} for issues."
                self.called_agent = self.team.planner.member_id
                self.responses[self.team.planner.member_id].append(("Returned from Planner", state['current_issue']))
            elif state['current_issue'].issue_status == Status.ABANDONED:
                logger.info(f"{self.team.planner.member_name} has abandoned the issue with issue Id: {state['current_issue'].issue_id}")

                state['agents_status'] = f"{self.team.planner.member_name} has abandoned issue ID: {state['current_issue'].issue_id}."
                self.called_agent = self.team.planner.member_id

                self.responses[self.team.planner.member_id].append(("Returned from Planner with an abandoned task.", state['current_issue']))
            elif state['current_issue'].issue_status == Status.AWAITING:
                logger.info(f"{self.team.planner.member_name} is requesting additional information for Issue ID: {state['current_issue'].issue_id}.")

                state['agents_status'] = f"{self.team.planner.member_name} is awaiting additional information for Issue ID: {state['current_issue'].issue_id}."

                self.called_agent = self.team.planner.member_id
                self.responses[self.team.planner.member_id].append(("Returned from Planner with a question", state['current_task'].question))                

        return state

    def call_reviewer(self, state: SupervisorState) -> SupervisorState:
        """
        """

        logger.info(f"{self.team.reviewer.member_name}: I have been called.")

        reviwer_result = self.team.reviewer.invoke({
            'project_name': state['project_name'],
            'project_path': state['project_path'],
            'license_text': state['license_text'],
            'requirements_document': state['requirements_document'].to_markdown(),
        })

        issues: IssuesQueue = reviwer_result['issues']

        if len(issues) > 0:
            logger.info(f"{self.team.reviewer.member_name}: Found some issues in the project.")
            state['issues'].extend(issues)
        else:
            logger.info(f"{self.team.reviewer.member_name}: No Issues were found.")

        return state

    def call_human(self, state: SupervisorState) -> SupervisorState:

        print(
            f"{self.team.architect.member_name} has completed the preparation of the project requirements document. "
            "Please proceed with a thorough review to ensure all criteria are met and aligned with project objectives.\n"
        )
        
        print(
            f"Document Path: {os.path.join(state['project_path'], 'docs/requirements.md')}\n"
        )
        
        print(
            "Does the requirements document meet the expected standards? Would you like to make any modifications? (Y/N): "
        )
        user_response = input()

        # Set modification requirement flag based on user response
        is_modification_required: bool = user_response.strip().lower() == 'y'

        if is_modification_required:
            human_feedback = ""
            while True:
                print("\nPlease provide your feedback: ")
                additional_feedback = input()
                human_feedback += f"\n{additional_feedback}"

                print("\nIs there additional feedback you'd like to provide? (Y/N): ")
                has_more_feedback = input()
                if has_more_feedback.strip().lower() != 'y':
                    break
            
            print("\nThank you for your feedback. It will be incorporated to regenerate the requirements document.")
        else:
            print(
                "\nYou have selected 'No', indicating that no modifications are required. "
                "Proceeding with the current version of the requirements document."
            )
            print("Continuing with project generation based on the current requirements.")
        if is_modification_required:
            state['current_task'].task_status = Status.INPROGRESS
            state['current_task'].additional_info += f"\nHuman feedback to incorporate:\n{human_feedback}"

        self.is_human_reviewed = True
    
        return state

    def delegator(self, state: SupervisorState) -> str:
        """
        Delegates the tasks across the agents based on the current project status.

        Parameters:
        state (SupervisorState): The current state of the project.

        Returns:
        str: The next action to be taken based on the project status.
        """

        if state['project_status'] == PStatus.NEW:
            # Project has been received by the team.
            # RAG(team member) now need to gather additonal information for the project
            # additional information? yep a more detailed information about the project.
            # user input would be to vague to start working on the project and results 
            # in a more generic output. so we need to more specific on what user is 
            # expecting. RAG holds the some standards documents and it fetches the 
            # relevant information related to the project to help team members 
            # efficient and qualified output.

            logger.info(f"Delegator: Invoking call_rag due to project status: {PStatus.NEW}")
            return 'call_rag'

        if state['project_status'] == PStatus.INITIAL:
            # Once the project is ready with additional information needed. Team can 
            # starting working on the project architect is first team member who 
            # receives the project details and prepares the the requirements out of it.
            # In this process if architect need aditional information thats when RAG 
            # comes into play at this phase of Project.
            if self.is_initial_additional_info_ready:
                logger.info(f"Delegator: Invoking call_architect due to Project Status: {PStatus.INITIAL}")
                return 'call_architect'
        elif state['project_status'] == PStatus.MONITORING:
            # During query answering phase by agents PROJECT_STATUS will be in this phase

            # RAG is the source for the information. It can fetch relevant information 
            # from vector DB for the given query.
            if state['current_task'].task_status == Status.AWAITING:
                logger.info(f"Delegator: Invoking call_rag due to Project Status: {PStatus.MONITORING} and Task Status: {Status.AWAITING}.")
                return 'call_rag'
        elif state['project_status'] == PStatus.EXECUTING:
            # During the execution phase, there are two key scenarios:
            # 1. The planner breaks down complex tasks into smaller, manageable planned tasks.
            # 2. Coder or tester completes the planned tasks.
            #
            # The `are_planned_tasks_in_progress` flag indicates whether there are any 
            # tasks in the planned tasks list.
            # If this flag is True, it means that planned tasks are the current priority.
            # If the list is empty, it signifies that there are no planned tasks, and 
            # any remaining tasks should be further broken down by the planner.
            if self.are_planned_tasks_in_progress:
                if state['current_planned_task'].is_function_generation_required:
                    if not state['current_planned_task'].is_test_code_generated:
                        logger.info(f"Delegator: Invoking call_test_code_generator due to Project Status: {PStatus.EXECUTING} and PlannedTask involving is_function_generation_required and is_test_code_generated.")
                        return 'call_test_code_generator'

                # Other conditions like is_code_generated from PlannedTask object is 
                # also useful to figure out if coder has already completed the task.
                if not state['current_planned_task'].is_code_generated:
                    logger.info(f"Delegator: Invoking call_test_code_generator due to Project Status: {PStatus.EXECUTING} and PlannedTask Status: {Status.NEW}.")
                    return 'call_coder'
            else:
                if state['current_task'].task_status in (Status.NEW, Status.RESPONDED):
                    logger.info(f"Delegator: Invoking call_planner due to Project Status: {PStatus.EXECUTING} and Task Status: {Status.NEW}.")
                    return 'call_planner'

            # occurs when architect just completed the assigned task(generating 
            # documents and tasks) and now supervisor has to assign tasks for planner.
            logger.info(f"Delegator: Invoking call_supervisor due to Project Status: {PStatus.EXECUTING}.")
            return 'call_supervisor'
        elif state['project_status'] == PStatus.REVIEWING:
            return 'call_reviewer'
        elif state['project_status'] == PStatus.RESOLVING:
            if self.are_planned_issues_in_progress:
                if state['current_planned_issue'].is_function_generation_required:
                    if not state['current_planned_issue'].is_test_code_generated:
                        logger.info(f"Delegator: Invoking call_test_code_generator due to Project Status: {PStatus.RESOLVING} and PlannedTask involving is_function_generation_required and is_test_code_generated.")
                        return 'call_test_code_generator'

                # Other conditions like is_code_generated from PlannedTask object is 
                # also useful to figure out if coder has already completed the task.
                if not state['current_planned_issue'].is_code_generated:
                    logger.info(f"Delegator: Invoking call_test_code_generator due to Project Status: {PStatus.RESOLVING} and PlannedTask Status: {Status.NEW}.")
                    return 'call_coder'
            else:
                if state['current_issue'].issue_status == Status.NEW:
                    logger.info(f"Delegator: Invoking call_planner due to Project Status: {PStatus.RESOLVING} and Task Status: {Status.NEW}.")
                    return 'call_planner'

            # occurs when architect just completed the assigned task(generating 
            # documents and tasks) and now supervisor has to assign tasks for planner.
            logger.info(f"Delegator: Invoking call_supervisor due to Project Status: {PStatus.RESOLVING}.")
            return 'call_supervisor'
        elif state['project_status'] == PStatus.HALTED:
            # There may be situations where the LLM (Language Learning Model) cannot 
            # make a decision or where human input is required to proceed. This could 
            # be due to ambiguity or intentional scenarios that need human judgment to 
            # ensure progress.

            if self.is_human_reviewed:
                return 'call_supervisor'
            
            logger.info(f"Delegator: Invoking call_human due to Project Status: {PStatus.HALTED}.")
            return "Human"

        logger.info("Delegator: Invoking update_state.")
        return "update_state"
