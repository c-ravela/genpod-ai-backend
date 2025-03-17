import ast
import os
from typing import TYPE_CHECKING, Dict, List, Tuple

from langchain_core.messages import AIMessage
from pydantic import ValidationError

from agents.base.base_agent import BaseAgent
from agents.supervisor.supervisor_state import SupervisorState
from context.agent_context import AgentContext
from context.context import GenpodContext
from context.task_context import TaskContext
from llms.llm import LLM
from models.constants import ChatRoles, PStatus, Status
from models.models import (Issue, IssuesQueue, PlannedIssue,
                           PlannedIssuesQueue, PlannedTask, PlannedTaskQueue,
                           RequirementsDocument, Task, TaskQueue)
from models.supervisor_models import QueryList
from prompts.supervisor_prompts import SupervisorPrompts
from utils.fuzzy_rag_cache import FuzzyRAGCache
from utils.logs.logging_utils import logger

if TYPE_CHECKING:
    from genpod.team import TeamMembers


class SupervisorAgent(BaseAgent[SupervisorState, SupervisorPrompts]):

    team: 'TeamMembers'

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        llm: LLM
    ) -> None:
        """
        Initializes a SupervisorAgent instance.

        Args:
            agent_id (str): The unique identifier for the agent.
            agent_name (str): The name of the agent.
            llm (LLM): An instance of the LLM class for generating responses.
        """
        super().__init__(
            agent_id,
            agent_name,
            SupervisorState(),
            SupervisorPrompts(),
            llm
        )
        self._genpod_context = GenpodContext.get_context()
        self.team = None

        # TODO - LOW: has to be moved to RAG agent
        self.rag_cache = FuzzyRAGCache()

        self.calling_agent: str = ""
        self.called_agent: str = ""
        self.responses: Dict[str, List[Tuple[str, Task]]] = {}
        logger.info("SupervisorAgent instance created successfully.")

    def setup_team(self, team: 'TeamMembers') -> None:
        """
        Sets up the team for the project.

        Args:
            team (TeamMembers): An instance of the TeamMembers class representing the team.

        Returns:
            None
        """
        if not team:
            logger.warning("No team provided during setup.")
        else:
            logger.info("Team setup initialized.")
        self.team = team
        logger.info("Team setup completed successfully.")

    # TODO - LOW: has to be moved to RAG agent
    def build_rag_cache(self, query: str) -> tuple[list[str], str]:
        """
        Constructs the RAG cache using the user-provided requirements.

        Args:
            query (str): User input that forms the basis of the RAG cache.

        Returns:
            Tuple[list[str], str]: A list of generated queries and the corresponding responses.
        """
        logger.info("Building RAG cache started.")
        context = ''
        max_attempts = 3
        validated_requirements_queries = QueryList(req_queries=[])

        while max_attempts > 0:
            try:
                logger.debug("Invoking LLM with query and context.")
                response = self.llm.invoke(
                    self.prompts.init_rag_questionaire_prompt, 
                    {'user_prompt': query, 'context': context}
                )
                req_queries: AIMessage = response.response
                req_queries = ast.literal_eval(req_queries.content)
                validated_requirements_queries = QueryList(req_queries=req_queries)
                logger.info("Successfully generated questions for the RAG cache and validated the queries.")
                break
            except (ValidationError, ValueError, SyntaxError) as e:
                logger.warning("Error while building RAG cache: %s", str(e))
                context += str(e)
                max_attempts -= 1

        if len(validated_requirements_queries.req_queries) > 0:
            logger.info("Processing validated queries.")
            final_response = ''

            for req_query in validated_requirements_queries.req_queries:
                result = self.rag_cache.get(req_query)
                if result is not None:
                    logger.debug("Cache hit for query: %s", req_query)
                    rag_response = result
                else:
                    logger.debug("Cache miss for query: %s", req_query)
                    logger.info(f"{self.team.rag.member_name} Agent called to handle query: %s", req_query)
                    result = self.team.rag.invoke({'question': req_query, 'max_hallucination': 3})
                    rag_response = result['generation']
                    self.rag_cache.add(req_query, rag_response)

                    logger.info("Agent response received: %s", rag_response)

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
                                f"Question: {req_query}\nAnswer: {rag_response}\n\n"
                            )
                        elif evaluation_result.content.startswith("INCOMPLETE"):
                            follow_up_query = evaluation_result.content.split(
                                "Follow-up Query:"
                            )[1].strip()

                            logger.info("Follow-up query needed: %s", follow_up_query)

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

                final_response += f"Question: {req_query}\nAnswer: {rag_response}\n\n"

            logger.info("RAG cache build completed successfully.")
            return (validated_requirements_queries.req_queries, final_response)

        logger.error("Failed to initialize project due to empty queries.")
        return ([], 'Failed to initialize project')

    def instantiate_state(self, state: SupervisorState) -> SupervisorState:
        """
        Initializes the state for the SupervisorAgent.

        Args:
            state (SupervisorState): The state object to be initialized.

        Returns:
            SupervisorState: The initialized state object.

        Raises:
            ValueError: If the team has not been initialized.
        """
        if self.team is None:
            error_message = (
                f"Error: Team for '{self.agent_name}' has not been initialized. "
                f"Current value of 'self.team': {self.team}. "
                "Please call 'setup_team' before proceeding."
            )
            logger.error(error_message)
            raise ValueError(error_message)

        logger.info("Initializing supervisor state.")
        default_state_values = {
            'project_name': '',
            'project_status': PStatus.RECEIVED,
            'agents_status': '',
            'microservice_name': '',
            'current_task': Task(),
            'current_planned_task': PlannedTask(),
            'current_planned_issue': PlannedIssue(is_function_generation_required=False),
            'current_issue': Issue(),
            'is_rag_query_answered': False,
            'rag_cache_queries': [],
            'issues': IssuesQueue(),
            'tasks': TaskQueue(),
            'human_feedback': [],
            'functions_skeleton': {},
            'test_code': '',
            'planned_tasks': PlannedTaskQueue(),
            'planned_issues': PlannedIssuesQueue(),
            'rag_retrieval': '',
            'requirements_document': RequirementsDocument(),
            'code_generation_plan_list': [],
            # internal
            'previous_project_status': PStatus.NONE,
            'rag_cache_building': '',
            'is_rag_cache_created': False,
            'is_initial_additional_info_ready': False,
            'are_planned_tasks_in_progress': False,
            'are_planned_issues_in_progress': False,
            'is_human_reviewed': False
        }
        for key, value in default_state_values.items():
            state[key] = BaseAgent.ensure_value(state.get(key), value)
            logger.debug(f"{self.agent_name}: {key} set to {state[key]}.")

        state['messages'] = BaseAgent.ensure_value(state['messages'], [
            (
                ChatRoles.USER,
                state['original_user_input']
            ),
            (
                ChatRoles.SYSTEM, 
                'A new project with the following details has been received from the'
                f'user: {state["original_user_input"]}'
            )
        ])

        self.responses = {member.member_id: [] for member in self.team.get_team_members_as_list()}
        logger.info("Supervisor state initialized: %s", state)
        logger.debug(
            "Supervisor state has been initialized successfully."
            f"current supervisor state: {state}"
        )
        self._genpod_context.update(microservice_id=state['microservice_id'])
        return state

    def call_rag(self, state: SupervisorState) -> SupervisorState:
        """
        Gathers the required information from the vector database (RAG cache).

        This method ensures the RAG cache is created if not already done, retrieves
        relevant data for the current task from the cache, or queries the RAG agent
        if needed. It updates the task and state based on the retrieved information.

        Args:
            state (SupervisorState): The current state of the SupervisorAgent.

        Returns:
            SupervisorState: The updated state after interacting with the RAG system.
        """
        logger.info(f"RAG agent '{self.team.rag.member_name}' has been invoked.")
        self.called_agent = self.team.rag.member_id

        # TODO - LOW: RAG cache creation has to be moved to RAG agent
        # check if rag cache was ready if not prepare one
        if not state['is_rag_cache_created']:
            logger.info(f"RAG cache creation initiated by '{self.team.rag.member_name}'.")

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
            try:
                queries, cache_content = self.build_rag_cache(state['original_user_input'])
                state['rag_cache_queries'] = queries
                state['rag_cache_building'] = cache_content
                state['is_rag_cache_created'] = True
                logger.info(
                    f"RAG cache created successfully with the following queries:\n{queries}"
                )
            except Exception as e:
                logger.error("Failed to create RAG cache: %s", str(e))
                raise e

        question = state['current_task'].question
        try:
            # Check RAG cache for the information first
            result = self.rag_cache.get(question)
            if result:
                logger.debug("Cache hit for query: \n%s", question)
                state['is_rag_query_answered'] = True
            else:
                logger.debug(f"Cache miss for query: '{question}'. Querying RAG agent.")
                additional_info = self.team.rag.invoke({
                    'question': question,
                    'max_hallucination': 3
                })

                result = additional_info['generation']
                state['is_rag_query_answered'] = additional_info['query_answered']
                self.rag_cache.add(question, result)

            logger.info(
                f"RAG agent '{self.team.rag.member_name}' provided a response for query: '{question}'"
            )
        except Exception as e:
            logger.error("Error while retrieving information from RAG: %s", str(e))
            raise e

        if state['project_status'] == PStatus.NEW:
            if state['current_task'].task_status == Status.NEW:
                logger.info(
                    f"Processing new project requirements. "
                    f"RAG agent '{self.team.rag.member_name}' is gathering additional information."
                )
                state['messages'] += [
                    (
                        ChatRoles.AI,
                        f"{self.team.rag.member_name}: Received user requirements and"
                        " gathering additional information."
                    )
                ]

                state['current_task'].additional_info = f"{result}\n{state['rag_cache_building']}"
                state['current_task'].task_status = Status.DONE
                state['is_initial_additional_info_ready'] = True
                state['rag_retrieval'] = result + "\n" + state['rag_cache_building']
                state['agents_status'] = f"Task completed by '{self.team.rag.member_name}'."

                self.responses[self.team.rag.member_id].append(
                    ("Returned from RAG database", state['current_task'])
                )
                return state
        elif state['project_status'] == PStatus.MONITORING:
            if state['current_task'].task_status == Status.AWAITING:
                logger.info(
                    f"RAG agent '{self.team.rag.member_name}' is responding to a team member's query."
                )

                state['messages'].append((
                    ChatRoles.AI,
                    f"{self.team.rag.member_name}: Received a query from team members and is preparing an answer."
                ))
                # TODO - MEDIUM: We are adding strings like `RAG_Response:` and using 
                # this word for conditional checks in a few places.
                # problem is performance degradation: the application slows down because 
                # we are searching for a small string in a very large
                # string. 06/09/2024 - conditional checks were removed, but still might 
                # need to reconsider the way we store info.
                state['current_task'].task_status = Status.RESPONDED
                state['current_task'].additional_info += f"\nRAG_Response:\n{result}"
                state['rag_retrieval'] += result
                state['agents_status'] = f"Query answered by '{self.team.rag.member_name}'."

                self.responses[self.team.rag.member_id].append(
                    ("Returned from RAG database serving a query", state['current_task'])
                )
                return state

        return state

    def call_architect(self, state: SupervisorState) -> SupervisorState:
        """
        Prepares the requirements document and addresses team members' queries by invoking the Architect agent.

        Args:
            state (SupervisorState): The current state of the SupervisorAgent.

        Returns:
            SupervisorState: The updated state after interacting with the Architect agent.
        """
        logger.info(f"Architect agent '{self.team.architect.member_name}' has been invoked.")
        self.called_agent = self.team.architect.member_id

        if state['project_status'] == PStatus.INITIAL:
            logger.info(f"'{self.team.architect.member_name}' started working on the requirements document.")

            try:
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
                current_task_status = architect_result['current_task'].task_status
                if current_task_status == Status.DONE:
                    logger.info(f"'{self.team.architect.member_name}' completed the requirements document.")
                    state['current_task'] = architect_result['current_task']
                    state['agents_status'] = f'{self.team.architect.member_name} completed'

                    self.responses[self.team.architect.member_id].append(
                        ("Returned from Architect", architect_result['tasks'])
                    )

                    state['tasks'].extend(architect_result['tasks'])
                    state['requirements_document'] = architect_result['requirements_document']
                    state['project_name'] = architect_result['project_name']
                    state['microservice_name'] = architect_result['project_name']
                elif current_task_status == Status.AWAITING: 
                    logger.info(
                        f"'{self.team.architect.member_name}' has a question that needs to be resolved."
                    )
                    state['current_task'] = architect_result['current_task']
                    state['agents_status'] = f'{self.team.architect.member_name} Awaiting'
                    self.responses[self.team.architect.member_id].append(
                        ("Returned from Architect with a question", architect_result['current_task'].question)
                    )
                else:
                    logger.warning(
                        f"Unexpected task status '{current_task_status}' returned by '{self.team.architect.member_name}'."
                    )

                return state
            except Exception as e:
                logger.error("Error while invoking the Architect agent: %s", str(e))
                raise e

        if state['project_status'] == PStatus.MONITORING:
            # Need to query Architect to get additional information for another agent
            # which will be present in called agent and that will never be updated when
            # returning
            logger.info(f"Querying Architect agent '{self.team.architect.member_name}' for additional information.")

            try:
                architect_result = self.team.architect.invoke({
                    'current_task': state['current_task'],
                    'project_status': state['project_status'],
                    'original_user_input': state['original_user_input'],
                    'project_path': state['project_path'],
                    'user_requested_standards': state['current_task'].additional_info,
                    'license_text': state['license_text'],
                    'messages': []
                })

                logger.info(f"Response received from Architect agent '{self.team.architect.member_name}'.")
                logger.debug("Architect Response: %r", architect_result['current_task'])

                # TODO: make architect to update the task_status to RESPONDED when done. 
                # else keep it awaiting meaning architect has no answer for the question.
                if architect_result['query_answered'] is True:
                    logger.info(f"Query successfully answered by '{self.team.architect.member_name}'.")
                    state['agents_status'] = f'{self.team.architect.member_name} completed'
                    self.responses[self.team.architect.member_id].append(
                        ("Returned from Architect serving a Query", architect_result['current_task'])
                    )
                    state['current_task'] = architect_result['current_task']
                else:
                    logger.warning(
                        f"'{self.team.architect.member_name}' could not answer the query. Checking for further action."
                    )
                    state['current_task'] = architect_result['current_task']
                    if not state['is_rag_query_answered']:
                        logger.info("RAG query unanswered; halting project for additional input.")
                        state['project_status'] = PStatus.HALTED

                return state
            except Exception as e:
                logger.error("Error while querying the Architect agent: %s", str(e))
                raise e

        logger.warning("Architect agent received unhandled project status. No changes made to the state.")
        return state

    def call_coder(self, state: SupervisorState) -> SupervisorState:
        """
        Invokes the Coder agent to handle planned tasks or issues based on the project status.

        Updates the state with the results returned by the Coder agent.

        Args:
            state (SupervisorState): The current state of the SupervisorAgent.

        Returns:
            SupervisorState: The updated state after interacting with the Coder agent.
        """
        logger.info(f"Coder agent '{self.team.coder.member_name}' has been invoked.")
        state['messages'] += [(
            ChatRoles.AI,
            'Calling Coder Agent'
        )]

        try:
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
                logger.info("Processing results for project status: EXECUTING.")
                state['current_planned_task'] = coder_result['current_planned_task']

                if state['current_planned_task'].task_status == Status.DONE:
                    logger.info(
                        f"{self.team.coder.member_name} successfully completed the task. "
                        f"Task ID: {state['current_planned_task'].task_id}."
                    )
                    state['code_generation_plan_list'].extend(
                        coder_result['code_generation_plan_list']
                    )
                    state['agents_status'] = f'{self.team.coder.member_name} has successfully completed the task.'
                elif state['current_planned_task'].task_status == Status.ABANDONED:
                    logger.warning(
                        f"{self.team.coder.member_name} abandoned the task. "
                        f"Abandoned Task ID: {state['current_planned_task'].task_id}."
                    )
                    state['agents_status'] = f"{self.team.coder.member_name} has abandoned the task."
                else:
                    logger.warning(
                        f"Unexpected task status for the planned task. "
                        f"Task ID: {state['current_planned_task'].task_id}, Status: {state['current_planned_task'].task_status}."
                    )

                self.called_agent = self.team.coder.member_id
                self.responses[self.team.coder.member_id].append(
                    ("Returned from Coder", state['current_planned_task'])
                )
            elif state['project_status'] == PStatus.RESOLVING:
                logger.info("Processing results for project status: RESOLVING.")
                state['current_planned_issue'] = coder_result['current_planned_issue']

                if state['current_planned_issue'].status == Status.DONE:
                    logger.info(
                        f"{self.team.coder.member_name} resolved the planned issue. "
                        f"Issue ID: {state['current_planned_issue'].id}."
                    )
                    state['code_generation_plan_list'].extend(coder_result['code_generation_plan_list'])
                elif state['current_planned_issue'].status == Status.ABANDONED:
                    logger.warning(
                        f"{self.team.coder.member_name} abandoned the planned issue. "
                        f"Issue ID: {state['current_planned_issue'].issue_id}."
                    )
                    state['agents_status'] = f"{self.team.coder.member_name} abandoned the issue resolution."
                else:
                    logger.warning(
                        f"Unexpected issue status for the planned issue. "
                        f"Issue ID: {state['current_planned_issue'].issue_id}, Status: {state['current_planned_issue'].status}."
                    )
            else:
                logger.warning(
                    f"Unhandled project status: {state['project_status']}. "
                    "No updates were made to the state."
                )

            return state
        except Exception as e:
            logger.error("Error during Coder agent invocation: %s", str(e))
            raise e

    def call_test_code_generator(self, state: SupervisorState) -> SupervisorState:
        """
        Invokes the Test Code Generator agent to handle planned tasks or issues based on the project status.

        Updates the state with results returned by the Test Code Generator agent.

        Args:
            state (SupervisorState): The current state of the SupervisorAgent.

        Returns:
            SupervisorState: The updated state after interacting with the Test Code Generator agent.
        """
        logger.info(f"Tester agent '{self.team.tests_generator.member_name}' has been invoked.")
        state['messages'] += [(
            ChatRoles.AI,
            'Calling Test Code Generator Agent'
        )]

        try:
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
                logger.info("Processing results for project status: EXECUTING.")
                state['current_planned_task'] = test_coder_result['current_planned_task']

                if state['current_planned_task'].task_status == Status.INPROGRESS:
                    logger.debug(
                        "Handling INPROGRESS status for planned task. Setting status to NEW as part of workaround."
                    )
                    # side effect of workaround added in TestGenerator.
                    # Doing this for coder.
                    state['current_planned_task'].task_status = Status.NEW

                    logger.info(
                        f"Test Code Generator successfully completed the work package. "
                        f"Task ID: {state['current_planned_task'].task_id}."
                    )
                    state['agents_status'] = f"{self.team.tests_generator.member_name} Completed"

                    # I feel if these are part of PlannedTask, It makes more sense then to 
                    # be in super state because for every coding task these varies.
                    state['test_code'] = test_coder_result['test_code']
                    state['functions_skeleton'] = test_coder_result['function_signatures']
                elif state['current_planned_task'].task_status == Status.ABANDONED:
                    logger.warning(
                        f"Test Code Generator abandoned the work package. "
                        f"Task ID: {state['current_planned_task'].task_id}."
                    )
                    state['agents_status'] = f'{self.team.tests_generator.member_name} abandoned task.'
                else:
                    logger.info(
                        "Test Code Generator awaiting additional information. "
                        f"Task ID: {state['current_planned_task'].task_id}."
                    )
                    state['agents_status'] = f'{self.team.tests_generator.member_name} Generator Awaiting'

                self.called_agent = self.team.tests_generator.member_id
                self.responses[self.team.tests_generator.member_id].append(
                    ("Returned from Test Code Generator", state['current_planned_task'])
                )
            elif state['project_status'] == PStatus.RESOLVING:
                logger.info("Processing results for project status: RESOLVING.")
                state['current_planned_issue'] = test_coder_result['current_planned_issue']

                if state['current_planned_issue'].status == Status.INPROGRESS:
                    logger.debug(
                        "Handling INPROGRESS status for planned issue. Setting status to NEW."
                    )
                    state['current_planned_issue'].status = Status.NEW
                elif state['current_planned_issue'].status == Status.ABANDONED:
                    logger.warning(
                        f"Test Code Generator abandoned the planned issue. "
                        f"Issue ID: {state['current_planned_issue'].issue_id}."
                    )
                    state['agent_status'] = f'{self.team.tests_generator.member_id} abandoned task.'
                else:
                    logger.warning(
                        "Unexpected status for planned issue. "
                        f"Issue ID: {state['current_planned_issue'].issue_id}, Status: {state['current_planned_issue'].status}."
                    )
            return state
        except Exception as e:
            logger.error("Error during Test Code Generator agent invocation: %s", str(e))
            raise e

    def call_supervisor(self, state: SupervisorState) -> SupervisorState:
        """
        Manages the team and makes decisions based on the current state of the project.

        Args:
            state (SupervisorState): The current state of the project.

        Returns:
            SupervisorState: The updated project state after processing.
        """
        logger.info(f"Supervisor Agent '{self.agent_name}' invoked.")
        self.called_agent = self.agent_id

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
                description='Retrieve additional context from RAG system',
                task_status=Status.NEW,
                additional_info='',
                question=state['original_user_input']
            )
            self._genpod_context.update(
                current_task=TaskContext(task_id=state['current_task'].task_id)
            )
            state['project_status'] = PStatus.NEW
            logger.info(
                f"Supervisor: Task created for RAG agent to gather additional information. "
                f"Project status updated to {state['project_status']}."
            )
            return state
        elif state['project_status'] == PStatus.NEW:
            # When the project status is 'NEW':
            # - The RAG Agent task is complete.
            # - The next step is to involve the architect to generate the requirements document for the team.

            # If the task is marked as done, it means the RAG agent has gathered the additional information 
            # needed for the team to begin the project.
            if state['current_task'].task_status == Status.DONE:
                if state['is_initial_additional_info_ready']:
                    state['project_status'] = PStatus.INITIAL

                    # create a new task for the architect
                    state['current_task'] = Task(
                        description=self.prompts.architect_call_prompt.format(),
                        task_status=Status.NEW,
                        additional_info=state['rag_retrieval'],
                        question=''
                    )
                    self._genpod_context.update(
                        current_task=TaskContext(task_id=state['current_task'].task_id)
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

                    logger.info(
                        f"Supervisor: Task for RAG agent completed. "
                        f"Created new task for Architect. Project status updated to {state['project_status']}."
                    )
                else:
                    logger.warning(
                        "Supervisor: Task marked as DONE, but 'is_initial_additional_info_ready' is False. "
                        "Check if additional information is missing."
                    )
            else:
                logger.warning(
                    f"Supervisor: Project status is {PStatus.NEW}, but task status is not DONE. "
                    f"Current task status: {state['current_task'].task_status}."
                )
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
                if not state['is_human_reviewed']:
                    state['project_status'] = PStatus.HALTED

                    logger.info(
                        "Supervisor: Architect completed the requirements document. "
                        "Waiting for human review."
                    )
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

                    logger.info(
                        "Supervisor: Architect completed requirements. "
                        f"Project status updated to {state['project_status']}."
                    )
            elif state['current_task'].task_status == Status.AWAITING:
                # Architect need additional information to complete the assigned task. 
                # architect provides query in the task packet use it to query RAG.
                state['previous_project_status'] = state['project_status']
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

                logger.info(
                    "Supervisor: Architect requested additional information. "
                    f"Project status updated to {state['project_status']}."
                )
            else:
                logger.warning(
                    f"Supervisor: Project status is {PStatus.INITIAL}, but task status is neither DONE nor AWAITING. "
                    f"Current task status: {state['current_task'].task_status}."
                )

            return state
        elif state['project_status'] == PStatus.MONITORING:
            # When the project status is 'MONITORING':
            # - If the current task status is 'RESPONDED':
            #   - Change the project status back to the previous state and proceed 
            # with the next steps.

            if state['current_task'].task_status == Status.RESPONDED:
                state['project_status'] = state['previous_project_status']
                self.calling_agent = self.called_agent

                state['messages'] += [
                    (
                        ChatRoles.AI,
                        "Team has responded to the query from team member."
                    )
                ]

                logger.info(
                    "Supervisor: Query answered. "
                    f"Project status reverted to {state['project_status']}."
                )
            else:
                logger.warning(
                    f"Supervisor: Project status is {PStatus.MONITORING}, but task status is not RESPONDED. "
                    f"Current task status: {state['current_task'].task_status}."
                )

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
                logger.error(
                    f"Supervisor: Task not found in 'tasks' list. Exception: {e}"
                )
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
                    self._genpod_context.update(
                        current_task=TaskContext(task_id=state['current_task'].task_id)
                    )
            elif state['current_task'].task_status == Status.AWAITING:
                # Planner needs additional information
                # Architect was responsible for answering the query if not then rag 
                # comes into play.
                state['previous_project_status'] = state['project_status']
                state['project_status'] = PStatus.MONITORING
                self.calling_agent = self.called_agent
            elif state['current_task'].task_status == Status.INPROGRESS:
                # update the planned_task status in the list
                try:
                    state['planned_tasks'].update_item(state['current_planned_task'])
                except Exception as e:
                    logger.error(
                        f"Supervisor: Planned task not found in 'planned_tasks' list. Exception: {e}"
                    )

                if state['current_planned_task'].task_status in (Status.NONE, Status.DONE, Status.ABANDONED):
                    next_planned_task = state['planned_tasks'].get_next_item()

                    if next_planned_task is None:
                        state['are_planned_tasks_in_progress'] = False
                        state['current_task'].task_status = Status.DONE
                    else:
                        state['current_planned_task'] = next_planned_task
                        state['are_planned_tasks_in_progress'] = True
                        self.calling_agent = self.agent_id
            else:
                logger.warning(
                    f"Supervisor: Unexpected task status during EXECUTING phase. "
                    f"Current task status: {state['current_task'].task_status}."
                )
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
                logger.info("Supervisor: Issues found during REVIEWING. Project status updated to RESOLVING.")
            else:
                state['project_status'] = PStatus.DONE
                logger.info("Supervisor: No issues found during REVIEWING. Project status updated to DONE.")
            return state
        elif state['project_status'] == PStatus.RESOLVING:

            try:
                state['issues'].update_item(state['current_issue'])
            except Exception as e:
                logger.error(
                    f"Supervisor: Issue not found in 'issues' list. Exception: {e}"
                )

            if state['current_issue'].issue_status in (Status.DONE, Status.NONE, Status.ABANDONED):
                if state['issues'].has_pending_items():
                    state['current_issue'] = state['issues'].get_next_item()
                    logger.info("Supervisor: Moving to next issue for resolution.")
                    self.calling_agent = self.agent_id
                else:
                    state['project_status'] = PStatus.REVIEWING
                    logger.info("Supervisor: All issues resolved. Project status updated to REVIEWING.")
            elif state['current_issue'].issue_status == Status.INPROGRESS:
                try:
                    state['planned_issues'].update_item(state['current_planned_issue'])
                except Exception as e:
                    logger.error(
                        f"Supervisor: Planned issue not found in 'planned_issues' list. Exception: {e}"
                    )

                if state['current_planned_issue'].status in (Status.NONE, Status.DONE, Status.ABANDONED):
                    if state['planned_issues'].has_pending_items():
                        state['current_planned_issue'] = state['planned_issues'].get_next_item()
                        state['are_planned_issues_in_progress'] = True
                        self.calling_agent = self.agent_id
                        logger.info("Supervisor: Moving to next planned issue for resolution.")
                    else:
                        state['are_planned_issues_in_progress'] = False
                        state['current_issue'].issue_status = Status.DONE
                        logger.info("Supervisor: All planned issues resolved for the current issue.")
                else:
                    logger.warning(
                        f"Supervisor: Unexpected status for planned issue during RESOLVING phase. "
                        f"Current planned issue status: {state['current_planned_issue'].status}."
                    )
            else:
                logger.warning(
                    f"Supervisor: Unexpected issue status during RESOLVING phase. "
                    f"Current issue status: {state['current_issue'].issue_status}."
                )

            return state
        elif state['project_status'] == PStatus.HALTED:
            # When the project status is 'HALTED':
            # - The application requires human intervention to resolve issues and
            #  complete the task.

            if state['is_human_reviewed']:
                state['project_status'] = PStatus.INITIAL
                if state['current_task'].task_status == Status.INPROGRESS:
                    state['is_human_reviewed'] = False
                    logger.info("Supervisor: Human review completed. Project status updated to INITIAL.")
                else:
                    logger.warning(
                        f"Supervisor: Human review marked as completed, but task status is not INPROGRESS. "
                        f"Current task status: {state['current_task'].task_status}."
                    )
            else:
                logger.warning(
                    "Supervisor: Project is in HALTED status, but 'is_human_reviewed' is False. "
                    "Human intervention may still be required."
                )
            return state
        elif state['project_status'] == PStatus.DONE:
            # When the project status is 'DONE':
            # - All tasks have been completed.
            # - The requested output for the user is ready.

            # TODO: Figure out when this stage occurs and handle the logic
            logger.info("Supervisor: Project has been marked as DONE. All tasks and issues resolved.")
            return state
        else:
            logger.warning(
                f"Supervisor: Unhandled project status encountered. Current project status: {state['project_status']}."
            )
            return state

    def call_planner(self, state: SupervisorState) -> SupervisorState:
        """
        Invokes the Planner agent to handle planned tasks or issues based on the project status.

        Updates the state with results returned by the Planner agent.

        Args:
            state (SupervisorState): The current state of the SupervisorAgent.

        Returns:
            SupervisorState: The updated state after interacting with the Planner agent.
        """
        logger.info(f"Planner agent '{self.team.planner.member_name}' has been invoked.")
        try:
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
                logger.info("Processing results for project status: EXECUTING.")
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
                    logger.info(
                        f"{self.team.planner.member_name} successfully prepared planned tasks. "
                        f"Task ID: {state['current_task'].task_id}."
                    )
                    state['planned_tasks'].extend(planner_result['planned_tasks'])
                    state['agents_status'] = (
                        f"Work packages prepared by {self.team.planner.member_name}."
                    )
                    self.responses[self.team.planner.member_id].append(("Returned from Planner", state['current_task']))
                elif state['current_task'].task_status == Status.ABANDONED:
                    logger.warning(
                        f"{self.team.planner.member_name} abandoned the task. "
                        f"Task ID: {state['current_task'].task_id}."
                    )
                    state['agents_status'] = (
                        f"{self.team.planner.member_name} abandoned Task ID: {state['current_task'].task_id}."
                    )

                    self.responses[self.team.planner.member_id].append(("Returned from Planner with an abandoned task.", state['current_task']))
                elif state['current_task'].task_status == Status.AWAITING:
                    logger.info(
                        f"{self.team.planner.member_name} is requesting additional information. "
                        f"Task ID: {state['current_task'].task_id}."
                    )
                    state['agents_status'] = (
                        f"{self.team.planner.member_name} awaiting additional information for Task ID: {state['current_task'].task_id}."
                    )
                    self.responses[self.team.planner.member_id].append(("Returned from Planner with a question", state['current_task'].question))
            elif state['project_status'] == PStatus.RESOLVING:
                logger.info("Processing results for project status: RESOLVING.")
                state['current_issue'] = planner_result['current_issue']

                if state['current_issue'].issue_status == Status.INPROGRESS:
                    logger.info(
                        f"{self.team.planner.member_name} successfully prepared planned issues. "
                        f"Issue ID: {state['current_issue'].issue_id}."
                    )
                    state['planned_issues'].extend(planner_result['planned_issues'])
                    state['agents_status'] = (
                        f"Planned issues prepared by {self.team.planner.member_name}."
                    )
                    self.responses[self.team.planner.member_id].append(("Returned from Planner", state['current_issue']))
                elif state['current_issue'].issue_status == Status.ABANDONED:
                    logger.warning(
                        f"{self.team.planner.member_name} abandoned the issue. "
                        f"Issue ID: {state['current_issue'].issue_id}."
                    )
                    state['agents_status'] = (
                        f"{self.team.planner.member_name} abandoned Issue ID: {state['current_issue'].issue_id}."
                    )
                    self.responses[self.team.planner.member_id].append(("Returned from Planner with an abandoned task.", state['current_issue']))
                elif state['current_issue'].issue_status == Status.AWAITING:
                    logger.info(
                        f"{self.team.planner.member_name} is requesting additional information. "
                        f"Issue ID: {state['current_issue'].issue_id}."
                    )
                    state['agents_status'] = (
                        f"{self.team.planner.member_name} awaiting additional information for Issue ID: {state['current_issue'].issue_id}."
                    )
                    self.responses[self.team.planner.member_id].append(("Returned from Planner with a question", state['current_task'].question))                

            self.called_agent = self.team.planner.member_id
            return state
        except Exception as e:
            logger.error("Error during Planner agent invocation: %s", str(e))
            raise e

    def call_reviewer(self, state: SupervisorState) -> SupervisorState:
        """
        Invokes the Reviewer agent to analyze the project and identify potential issues.

        Updates the state with the results returned by the Reviewer agent.

        Args:
            state (SupervisorState): The current state of the SupervisorAgent.

        Returns:
            SupervisorState: The updated state after interacting with the Reviewer agent.
        """
        logger.info(f"{self.team.reviewer.member_name}: I have been called to review the project.")
        try:
            reviwer_result = self.team.reviewer.invoke({
                'project_name': state['project_name'],
                'project_path': state['project_path'],
                'license_text': state['license_text'],
                'requirements_document': state['requirements_document'].to_markdown(),
            })

            issues: IssuesQueue = reviwer_result['issues']

            if len(issues) > 0:
                logger.info(
                    f"{self.team.reviewer.member_name}: Found {len(issues)} issue(s) in the project."
                )
                state['issues'].extend(issues)
                logger.debug("The following issues were identified by the Reviewer: %s", issues)
            else:
                logger.info(f"{self.team.reviewer.member_name}: No issues were found in the project.")

            return state
        except Exception as e:
            logger.error("Error during Reviewer agent invocation: %s", str(e))
            raise e

    def call_human(self, state: SupervisorState) -> SupervisorState:
        """
        Engages with a human reviewer to validate or modify the project requirements document.

        Updates the state based on the human review and feedback.

        Args:
            state (SupervisorState): The current state of the SupervisorAgent.

        Returns:
            SupervisorState: The updated state after incorporating human feedback.
        """
        print(
            f"{self.team.architect.member_name} has completed the preparation of the project requirements document. "
            "Please proceed with a thorough review to ensure all criteria are met and aligned with project objectives.\n"
        )
        
        requirements_document_path = os.path.join(state['project_path'], 'docs/requirements.md')
        print(f"Document Path: {requirements_document_path}\n")
        
        print(
            "Does the requirements document meet the expected standards? "
            "Would you like to make any modifications? (Y/N): "
        )
        user_response = input().strip().lower()

        # Set modification requirement flag based on user response
        is_modification_required: bool = user_response == 'y'

        human_feedback = ""
        if is_modification_required:
            print("\nYou have indicated that modifications are required. Please provide your feedback.")
            while True:
                print("\nPlease provide your feedback: ")
                additional_feedback = input().strip()
                human_feedback += f"\n{additional_feedback}"

                print("\nWould you like to provide additional feedback? (Y/N): ")
                has_more_feedback = input().strip().lower()
                if has_more_feedback != 'y':
                    break
            
            print(
                "\nThank you for your feedback. It will be incorporated into the requirements document for regeneration."
            )
            state['current_task'].task_status = Status.INPROGRESS
            state['current_task'].additional_info += (
                f"\nHuman feedback to incorporate:\n{human_feedback}"
            )
        else:
            print(
                "\nYou have selected 'No', indicating that no modifications are required. "
                "The current version of the requirements document will be used."
            )
            print("Proceeding with project generation based on the current requirements.")

        state['is_human_reviewed'] = True
    
        return state

    def delegator(self, state: SupervisorState) -> str:
        """
        Delegates tasks across agents based on the current project status.

        Args:
            state (SupervisorState): The current state of the project.

        Returns:
            str: The next action to be taken based on the project status.
        """
        logger.info("Delegator: Assessing the project state for task delegation.")

        if state['project_status'] == PStatus.NEW:
            # Project has been received by the team.
            # RAG(team member) now need to gather additonal information for the project
            # additional information? yep a more detailed information about the project.
            # user input would be to vague to start working on the project and results 
            # in a more generic output. so we need to more specific on what user is 
            # expecting. RAG holds the some standards documents and it fetches the 
            # relevant information related to the project to help team members 
            # efficient and qualified output.
            self._genpod_context.update(
                current_agent=AgentContext(
                    agent_id=self.team.rag.member_id,
                    agent_name=self.team.rag.member_name,
                )
            )
            logger.info(f"Delegator: Project is in {PStatus.NEW} status. Invoking call_rag to gather additional information.")
            return 'call_rag'

        if state['project_status'] == PStatus.INITIAL:
            # Once the project is ready with additional information needed. Team can 
            # starting working on the project architect is first team member who 
            # receives the project details and prepares the the requirements out of it.
            # In this process if architect need aditional information thats when RAG 
            # comes into play at this phase of Project.
            if state['is_initial_additional_info_ready']:
                self._genpod_context.update(
                    current_agent=AgentContext(
                        agent_id=self.team.architect.member_id,
                        agent_name=self.team.architect.member_name,
                    )
                )
                logger.info("Delegator: Project is in INITIAL status with additional information ready. Invoking call_architect.")
                return 'call_architect'
        elif state['project_status'] == PStatus.MONITORING:
            # During query answering phase by agents PROJECT_STATUS will be in this phase

            # RAG is the source for the information. It can fetch relevant information 
            # from vector DB for the given query.
            if state['current_task'].task_status == Status.AWAITING:
                self._genpod_context.update(
                    current_agent=AgentContext(
                        agent_id=self.team.rag.member_id,
                        agent_name=self.team.rag.member_name,
                    )
                )
                logger.info("Delegator: Project is in MONITORING status. Invoking call_rag to handle an awaiting query.")
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
            if state['are_planned_tasks_in_progress']:
                if state['current_planned_task'].is_function_generation_required:
                    if not state['current_planned_task'].is_test_code_generated:
                        self._genpod_context.update(
                            current_agent=AgentContext(
                                agent_id=self.team.tests_generator.member_id,
                                agent_name=self.team.tests_generator.member_name,
                            )
                        )
                        logger.info(
                            "Delegator: Project is in EXECUTING status with a planned task requiring function generation and test code generation. Invoking call_test_code_generator."
                        )
                        return 'call_test_code_generator'

                # Other conditions like is_code_generated from PlannedTask object is 
                # also useful to figure out if coder has already completed the task.
                if not state['current_planned_task'].is_code_generated:
                    self._genpod_context.update(
                        current_agent=AgentContext(
                            agent_id=self.team.coder.member_id,
                            agent_name=self.team.coder.member_name,
                        )
                    )
                    logger.info(
                        "Delegator: Project is in EXECUTING status with a planned task requiring code generation. Invoking call_coder."
                    )
                    return 'call_coder'
            else:
                if state['current_task'].task_status in (Status.NEW, Status.RESPONDED):
                    self._genpod_context.update(
                        current_agent=AgentContext(
                            agent_id=self.team.planner.member_id,
                            agent_name=self.team.planner.member_name,
                        )
                    )
                    logger.info(
                        "Delegator: Project is in EXECUTING status with tasks requiring planning. Invoking call_planner."
                    )
                    return 'call_planner'

            self._genpod_context.update(
                current_agent=AgentContext(
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                )
            )
            # occurs when architect just completed the assigned task(generating 
            # documents and tasks) and now supervisor has to assign tasks for planner.
            logger.info("Delegator: Project is in EXECUTING status with tasks pending assignment. Invoking call_supervisor.")
            return 'call_supervisor'
        elif state['project_status'] == PStatus.REVIEWING:
            logger.info("Delegator: Project is in REVIEWING status. Invoking call_reviewer.")
            self._genpod_context.update(
                current_agent=AgentContext(
                    agent_id=self.team.reviewer.member_id,
                    agent_name=self.team.reviewer.member_name,
                )
            )
            return 'call_reviewer'
        elif state['project_status'] == PStatus.RESOLVING:
            if state['are_planned_issues_in_progress']:
                if state['current_planned_issue'].is_function_generation_required:
                    if not state['current_planned_issue'].is_test_code_generated:
                        self._genpod_context.update(
                            current_agent=AgentContext(
                                agent_id=self.team.tests_generator.member_id,
                                agent_name=self.team.tests_generator.member_name,
                            )
                        )
                        logger.info(
                            "Delegator: Project is in RESOLVING status with a planned issue requiring function generation and test code generation. Invoking call_test_code_generator."
                        )
                        return 'call_test_code_generator'

                # Other conditions like is_code_generated from PlannedTask object is 
                # also useful to figure out if coder has already completed the task.
                if not state['current_planned_issue'].is_code_generated:
                    self._genpod_context.update(
                        current_agent=AgentContext(
                            agent_id=self.team.coder.member_id,
                            agent_name=self.team.coder.member_name,
                        )
                    )
                    logger.info(
                        "Delegator: Project is in RESOLVING status with a planned issue requiring code generation. Invoking call_coder."
                    )
                    return 'call_coder'
            else:
                if state['current_issue'].issue_status == Status.NEW:
                    self._genpod_context.update(
                        current_agent=AgentContext(
                            agent_id=self.team.planner.member_id,
                            agent_name=self.team.planner.member_name,
                        )
                    )
                    logger.info(
                        "Delegator: Project is in RESOLVING status with a new issue requiring planning. Invoking call_planner."
                    )
                    return 'call_planner'

            # occurs when architect just completed the assigned task(generating 
            # documents and tasks) and now supervisor has to assign tasks for planner.
            logger.info("Delegator: Project is in RESOLVING status with tasks pending assignment. Invoking call_supervisor.")
            return 'call_supervisor'
        elif state['project_status'] == PStatus.HALTED:
            # There may be situations where the LLM (Language Learning Model) cannot 
            # make a decision or where human input is required to proceed. This could 
            # be due to ambiguity or intentional scenarios that need human judgment to 
            # ensure progress.

            if state['is_human_reviewed']:
                self._genpod_context.update(
                    current_agent=AgentContext(
                        agent_id=self.agent_id,
                        agent_name=self.agent_name
                    )
                )
                logger.info("Delegator: Project is in HALTED status and has been reviewed by a human. Invoking call_supervisor.")
                return 'call_supervisor'
            
            self._genpod_context.update(current_agent=AgentContext())
            logger.info("Delegator: Project is in HALTED status requiring human review. Invoking call_human.")
            return "Human"

        self._genpod_context.update(
            current_agent=AgentContext(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
            )
        )
        logger.info("Delegator: No specific action matched. Invoking update_state.")
        return "update_state"
