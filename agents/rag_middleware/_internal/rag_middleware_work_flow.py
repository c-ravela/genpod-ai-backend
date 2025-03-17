from typing import Dict, List

from agents.rag_middleware._internal.rag_middleware_mode_enum import (
    RAGMiddlewareMode, RAGQueryStage)
from agents.rag_middleware._internal.rag_middleware_node_enum import \
    RAGMiddlewareNode
from agents.rag_middleware._internal.rag_middleware_prompt import \
    RAGMiddlewarePrompts
from agents.rag_middleware._internal.rag_middleware_state import (
    RAGMiddlewareOutput, RAGMiddlewareState)
from agents.rag_middleware.registry import RagAgentEntry
from core.agent import BaseAgent
from core.decorators import (handle_errors_and_reset, record_node,
                             route_on_errors)
from core.state import RAGQueryInput, RAGQueryOutput
from core.workflow import BaseWorkFlow
from llms import LLM
from models import PStatus, RagResponseType, RagSelectionResponse, Status, Task
from utils.logs.logging_utils import logger

ERROR_THRESHOLD = 3


class RAGMiddlewareWorkFlow(BaseWorkFlow[RAGMiddlewarePrompts]):
    """
    Workflow class for RAG middleware processing.

    This workflow is responsible for processing incoming queries by selecting an appropriate 
    retrieval-augmented generation (RAG) agent to answer the query and returning the resulting response.
    It leverages a language model to determine the best-suited agent based on available agent descriptions 
    and the query content, while also managing error tracking and task transitions to ensure robust performance.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        llm: LLM,
        rag_agent_entries: List[RagAgentEntry],
        dummy_agent_id: str,
        research_agent: BaseAgent,
        use_research_agent: bool = False
    ) -> None:
        """
        Initializes the RAG Middleware Workflow.

        Args:
            agent_id (str): The unique identifier for the middleware agent.
            agent_name (str): The name of the middleware agent.
            llm (LLM): The language model instance used for agent selection and query processing.
            rag_agent_entries (List[RagAgentEntry]): A list of registered RAG agent entries. Each entry contains a RAG agent and its description.
            dummy_agent_id (str): The ID of the fallback dummy agent.
            research_agent (BaseAgent): The research agent to be used as a fallback.
            use_research_agent (bool): Flag indicating whether the research agent should be invoked.
        """
        self.rag_agent_dict: Dict[str, RagAgentEntry] = {
            entry.agent.id: entry for entry in rag_agent_entries
        }
        logger.info("Initialized RAGMiddlewareWorkFlow with %d RAG agents.", len(self.rag_agent_dict))

        self.dummy_agent_id = dummy_agent_id
        self.research_agent = research_agent
        self.use_research_agent = use_research_agent

        super().__init__(
            agent_id,
            agent_name,
            RAGMiddlewarePrompts(),
            llm
        )

    @route_on_errors
    def router(self, state: RAGMiddlewareState) -> str:
        """
        Router function that directs the processing flow based on the current mode stage.
        
        Args:
            state (RAGMiddlewareState): The current middleware state.
            
        Returns:
            str: A string indicating the next node to process.
        """
        func_name = "router"
        logger.info("%s: Routing for operational mode '%s' and current mode stage '%s'.",
                    func_name, state.operational_mode, state.current_mode_stage)

        if state.operational_mode == RAGMiddlewareMode.PROCESSING_QUERY:
            if state.current_mode_stage == RAGQueryStage.EVALUATE_QUERY:
                logger.info("%s: Routing to QUERY_EVALUATION node.", func_name)
                return str(RAGMiddlewareNode.QUERY_EVALUATION)
            elif state.current_mode_stage == RAGQueryStage.SELECT_AGENT:
                logger.info("%s: Routing to AGENT_SELECTION node.", func_name)
                return str(RAGMiddlewareNode.AGENT_SELECTION)
            elif state.current_mode_stage == RAGQueryStage.FORWARD_TO_RAG:
                logger.info("%s: Routing to FORWARD_TO_RAG node.", func_name)
                return str(RAGMiddlewareNode.FORWARD_TO_RAG)
            elif state.current_mode_stage == RAGQueryStage.REFINE_RESPONSE:
                logger.info("%s: Routing to RESPONSE_REFINEMENT node.", func_name)
                return str(RAGMiddlewareNode.RESPONSE_REFINEMENT)
            elif state.current_mode_stage == RAGQueryStage.FALLBACK_RESEARCH:
                return str(RAGMiddlewareNode.RESEARCH)
            elif state.current_mode_stage == RAGQueryStage.FINISHED:
                logger.info("%s: Routing to EXIT node.", func_name)
                return str(RAGMiddlewareNode.EXIT)
            else:
                logger.warning("Router: Unrecognized mode stage '%s'. Defaulting to EXIT.", state.current_mode_stage)
                return str(RAGMiddlewareNode.EXIT)
        else:
            logger.info("%s: Operational mode '%s' is not PROCESSING_QUERY. Defaulting to EXIT.", func_name, state.operational_mode)
            return str(RAGMiddlewareNode.EXIT)

    @record_node(RAGMiddlewareNode.ENTRY)
    def entry_node(self, state: RAGMiddlewareState) -> RAGMiddlewareState:
        """
        Entry node for the RAG middleware workflow.

        This node initializes the processing of a query by setting the operational mode and
        the current stage if the project status indicates monitoring and the task is new.

        Args:
            state (RAGMiddlewareState): The current state of the middleware.
        
        Returns:
            RAGMiddlewareState: The updated state with operational mode and stage set.
        """
        func_name = "entry_node"
        logger.info("%s: Entering entry node.", func_name)

        try:
            if state.project_status == PStatus.MONITORING:
                if state.current_task.task_status == Status.NEW:
                    state.response_type = RagResponseType.NOT_ADDRESSED
                    state.response = ""
                    state.selection_details = {}
                    state.selected_rag_agent = {}
                    state.operational_mode = RAGMiddlewareMode.PROCESSING_QUERY
                    state.current_mode_stage = RAGQueryStage.EVALUATE_QUERY
                    logger.info("%s: Set operational mode to PROCESSING_QUERY and stage to EVALUATE_QUERY.", func_name)
        except Exception as e:
            logger.error("Agent '%s': Function '%s': Error in entry_node: %s", self.agent_name, func_name, e, exc_info=True)
            raise

        return state

    @record_node(RAGMiddlewareNode.QUERY_EVALUATION)
    @handle_errors_and_reset
    def query_evaluation_node(self, state: RAGMiddlewareState) -> RAGMiddlewareState:
        """
        Evaluates the incoming query by checking the in-memory cache and error registry.

        The node performs the following:
          - Retrieves agent_id, task_id, and query from state.
          - Cleans up error registry entries if the agent has moved to a new task.
          - Checks the in-memory lookup for a cached response.
          - Verifies whether the error count for the agent/task exceeds the threshold.
          - If a cached response is found or errors exceed threshold, updates the state accordingly.
          - Otherwise, sets the stage to SELECT_AGENT.
        
        Args:
            state (RAGMiddlewareState): The current state of the middleware.
        
        Returns:
            RAGMiddlewareState: The updated state after query evaluation.
        """
        func_name = 'query_evaluation_node'
  
        agent_id = state.agent_id
        task_id = state.task_id
        query = state.query

        logger.info("%s: Starting query evaluation for agent '%s', task '%s' with query: '%s'.", func_name, agent_id, task_id, query)
        logger.debug("%s: Entering function with query '%s' for agent '%s' and task '%s'.", func_name, query, agent_id, task_id)

        # Clean up error registry entries for this agent if they've moved to a new task.
        logger.debug("%s: Checking if error registry cleanup is needed for agent '%s' with current task '%s'.", func_name, agent_id, task_id)
        self._reset_or_cleanup_errors_for_agent(state, agent_id, task_id)
        logger.debug("%s: Completed error registry cleanup for agent '%s'.", func_name, agent_id)
        
        logger.debug("%s: Checking in-memory lookup for query '%s'.", func_name, query)
        cached_entry = state.in_memory_query_lookup.get(query)
        if cached_entry is not None:
            logger.info("%s: Query '%s' found in in-memory lookup.", func_name, query)
            state.response = cached_entry
            state.response_type = RagResponseType.FROM_CACHE
            state.current_mode_stage = RAGQueryStage.FINISHED
            logger.debug("%s: Returning state with cached response.", func_name)
            return state

        # Use a key based on agent and task to track error count.
        key = self._make_error_key(agent_id, task_id)
        current_error_count = state.error_registry.get(key, 0)
        logger.debug("%s: Current error count for agent '%s' and task '%s' is %d.", func_name, agent_id, task_id, current_error_count)

        # If the error count exceeds the threshold, reject the query.
        if current_error_count >= ERROR_THRESHOLD:
            error_msg = (
                f"Agent '{agent_id}' has exceeded the error threshold for task '{task_id}'. "
                "No further queries will be processed for this task."
            )
            logger.warning("%s: %s", func_name, error_msg)
            state.response = error_msg
            state.response_type = RagResponseType.REJECTED
            state.current_mode_stage = RAGQueryStage.FINISHED
            logger.debug("%s: Returning state with rejection due to error threshold.", func_name)
            return state

        # If no cached result and error threshold not reached, move to the next stage.
        state.current_mode_stage = RAGQueryStage.SELECT_AGENT
        logger.debug("%s: No cached response and error threshold not reached. Moving to stage: %s", func_name, state.current_mode_stage)
        logger.info("%s: Query '%s' requires further processing. Proceeding to agent selection.", func_name, query)
        return state

    @record_node(RAGMiddlewareNode.AGENT_SELECTION)
    @handle_errors_and_reset
    def agent_selection_node(self, state: RAGMiddlewareState) -> RAGMiddlewareState:
        """
        Selects the appropriate RAG agent to process the query.

        This node performs the following steps:
        1. Constructs a formatted list of available RAG agents and their descriptions.
        2. If no agents are registered, it updates the state to indicate that no suitable agent is available
            and transitions to the FALLBACK_RESEARCH stage.
        3. Otherwise, it invokes the LLM using the agent selection prompt with the agent list and the query.
        4. Parses the LLM response to extract the selected agent ID.
        5. If the selected agent is the dummy agent or cannot be found, it updates the state accordingly and
            transitions to FALLBACK_RESEARCH.
        6. If a valid agent is selected, it updates the state with the agent's details and selection metrics,
            and sets the next stage to FORWARD_TO_RAG.

        Args:
            state (RAGMiddlewareState): The current middleware state, including the query and available agent information.

        Returns:
            RAGMiddlewareState: The updated state with the selected RAG agent and the appropriate processing stage.
        """
        func_name = "agent_selection_node"
        logger.info("%s: Starting agent selection process.", func_name)

        # Check if there are any registered RAG agents.
        if not self.rag_agent_dict:
            logger.warning(
                "%s: No RAG agents registered. Marking state as NO_AGENT_AVAILABLE and transitioning to FALLBACK_RESEARCH.",
                func_name
            )
            state.response_type = RagResponseType.NO_AGENT_AVAILABLE
            state.current_mode_stage = RAGQueryStage.FALLBACK_RESEARCH
            return state

        agent_list_str = "\n".join(
            f"{agent_id}: {entry.description}" for agent_id, entry in self.rag_agent_dict.items()
        )
        logger.debug("%s: Constructed agent list:\n%s", func_name, agent_list_str)

        llm_output = self.invoke_with_pydantic_model(
            self.prompts.rag_agent_selection_prompt,
            {"agent_list": agent_list_str, "query": state.query},
            RagSelectionResponse
        )
        logger.debug("%s: Received LLM output: %s", func_name, llm_output.response)

        selected_rag_agent_id = llm_output.response.rag_agent_id.strip()
        logger.info("%s: LLM selected RAG agent ID: %s", func_name, selected_rag_agent_id)

        if selected_rag_agent_id == self.dummy_agent_id:
            logger.info(
                "%s: Dummy agent selected. No suitable RAG agent available. Transitioning to FALLBACK_RESEARCH.",
                func_name
            )
            state.response_type = RagResponseType.NO_AGENT_AVAILABLE
            state.current_mode_stage = RAGQueryStage.FALLBACK_RESEARCH
            return state

        agent_entry = self.rag_agent_dict.get(selected_rag_agent_id)
        if agent_entry is None:
            logger.warning(
                "%s: No agent found for the selected agent ID '%s'. Transitioning to FALLBACK_RESEARCH.",
                func_name, selected_rag_agent_id
            )
            state.response_type = RagResponseType.NO_AGENT_AVAILABLE
            state.current_mode_stage = RAGQueryStage.FALLBACK_RESEARCH
            return state

        state.selected_rag_agent = {
            'id': agent_entry.agent.id,
            'name': agent_entry.agent.name,
            'description': agent_entry.description
        }
        state.selection_details = llm_output.response.details

        state.current_mode_stage = RAGQueryStage.FORWARD_TO_RAG
        logger.debug("%s: Updated state.current_mode_stage to %s.", func_name, state.current_mode_stage)
        return state

    @record_node(RAGMiddlewareNode.FORWARD_TO_RAG)
    @handle_errors_and_reset
    def forward_to_rag_node(self, state: RAGMiddlewareState) -> RAGMiddlewareState:
        """
        Forwards the query to the selected RAG agent and captures its response.

        The node performs the following:
          - Retrieves the selected RAG agent from the state.
          - Constructs the input state for the RAG agent.
          - Invokes the RAG agent with the input and captures the raw output.
          - Parses the raw output into a RAGQueryOutput and updates the state.
          - Sets the next processing stage to REFINE_RESPONSE.
        
        Args:
            state (RAGMiddlewareState): The current state containing the selected RAG agent and query.
        
        Returns:
            RAGMiddlewareState: The updated state with the RAG agent's output and next stage set.
        """
        func_name = "forward_to_rag_node"
        logger.info("%s: Forwarding query to the selected RAG agent.", func_name)

        rag_agent = self.rag_agent_dict.get(state.selected_rag_agent['id']).agent
        logger.debug("%s: Selected RAG agent: %s", func_name, rag_agent)

        self._invoke_agent(
            agent=rag_agent,
            task_description="Task to generate an appropriate answer for the incoming request for information.",
            state=state
        )

        state.current_mode_stage = RAGQueryStage.REFINE_RESPONSE
        logger.info("%s: Updated processing stage to '%s'.", func_name, state.current_mode_stage)
        return state

    @record_node(RAGMiddlewareNode.RESPONSE_REFINEMENT)
    @handle_errors_and_reset
    def response_refinement_node(self, state: RAGMiddlewareState) -> RAGMiddlewareState:
        """
        Node responsible for refining the response from the RAG agent.

        This node processes the raw output generated by the RAG agent to ensure that the response
        meets expected quality and formatting standards. It performs actions such as:
        - Trimming unnecessary whitespace.
        - Validating that a response was generated.
        - Updating the response_type based on the content.
        - Augmenting metadata to indicate that the response was refined.

        If the refined response is empty, the response_type is set to 'rag_not_answered' and a
        default message is provided.

        Args:
            state (RAGMiddlewareState): The current state of the RAG middleware, including the raw RAG agent output.
        
        Returns:
            RAGMiddlewareState: The updated state with the refined response.
        """
        func_name = "response_refinement_node"
        logger.info("%s: Starting response refinement.", func_name)

        rag_output: RAGQueryOutput = state.rag_agent_output
        logger.debug("%s: Raw RAG output: %s", func_name, rag_output)

        if self.use_research_agent and rag_output.response_type not in (RagResponseType.ANSWERED, RagResponseType.REJECTED, RagResponseType.FROM_CACHE):
            state.current_mode_stage = RAGQueryStage.FALLBACK_RESEARCH
            return state

        refined_response = rag_output.response.strip()

        state.rag_agent_output = rag_output
        state.response = refined_response
        state.response_type = rag_output.response_type

        state.current_mode_stage = RAGQueryStage.FINISHED
        logger.info("%s: Completed response refinement. Updated processing stage to FINISHED.", func_name)
    
        return state

    @record_node(RAGMiddlewareNode.RESEARCH)
    @handle_errors_and_reset
    def research_agent_node(self, state: RAGMiddlewareState) -> RAGMiddlewareState:
        """
        Invokes the research agent to generate a response when the RAG agent's output is insufficient.

        This node is called after the response refinement node if the response type is neither ANSWERED nor REJECTED.
        The research agent is invoked with the same input format as the RAG agent, and its output is processed in a similar manner.

        Args:
            state (RAGMiddlewareState): The current middleware state.
        
        Returns:
            RAGMiddlewareState: The updated state with the research agent's output.
        """
        func_name = "research_agent_node"
        logger.info("%s: Invoking research agent fallback for query.", func_name)

        state.selected_rag_agent = {
            'id': self.research_agent.id,
            'name': self.research_agent.name,
            'description': self.research_agent.description
        }

        self._invoke_agent(
            agent=self.research_agent,
            task_description="Task to generate answer using research agent fallback.",
            state=state
        )

        state.current_mode_stage = RAGQueryStage.REFINE_RESPONSE
        logger.info("%s: Research agent invocation complete. Response updated.", func_name)

        return state

    @record_node(RAGMiddlewareNode.EXIT)
    def exit_node(self, state: RAGMiddlewareState) -> RAGMiddlewareOutput:
        """
        Exit node for the RAG middleware process.

        This node is responsible for finalizing the processing of a query. If the middleware is in 
        PROCESSING_QUERY mode and the current mode stage is FINISHED, it updates the task status to DONE.
        Otherwise, it logs a warning to indicate that the processing has not finished as expected.
        
        Args:
            state (RAGMiddlewareState): The current state of the RAG middleware.
        
        Returns:
            RAGMiddlewareOutput: The final output state of the RAG middleware.
        """
        func_name = "exit_node"
        logger.info("%s: Entering exit node with operational_mode '%s' and current_mode_stage '%s'.",
                    func_name, state.operational_mode, state.current_mode_stage)
        
        if state.operational_mode == RAGMiddlewareMode.PROCESSING_QUERY:
            if state.current_mode_stage == RAGQueryStage.FINISHED:
                logger.info("%s: Query processing is finished. Marking current task as DONE.", func_name)
                state.current_task.task_status = Status.DONE

                self._update_error_registry_and_cache(state, func_name)
            else:
                state.current_task.task_status = Status.INCOMPLETE
                logger.warning("%s: Operational mode is PROCESSING_QUERY but current mode stage is not FINISHED (current stage: '%s'). Setting task status to INCOMPLETE.",
                            func_name, state.current_mode_stage)
        else:
            logger.info("%s: Exiting node with operational_mode '%s'.", func_name, state.operational_mode)
        
        logger.info("%s: Exiting exit node. Final state returned.", func_name)
        return state
    
    def _reset_or_cleanup_errors_for_agent(self, state: RAGMiddlewareState, agent_id: str, current_task_id: str) -> None:
        """
        Resets or cleans up error entries for a given agent when a new task is detected.
        
        If the agent was previously working on a different task, remove all error registry entries
        for that agent that do not match the current task and initialize the error count for the current task.
        Also, update the record of the agent's last task.
        
        Args:
            state (RAGMiddlewareState): The current state containing the error registry and agent_last_task.
            agent_id (str): The unique identifier for the agent.
            current_task_id (str): The identifier for the current task.
        """
        func_name = '_reset_or_cleanup_errors_for_agent'
        logger.info("%s: Checking if cleanup is needed for agent '%s' with current task '%s'.", func_name, agent_id, current_task_id)

        current_key = self._make_error_key(agent_id, current_task_id)
    
        # Check if the agent has a recorded task that differs from the current task.
        if agent_id in state.agent_last_task and state.agent_last_task[agent_id] != current_task_id:
            logger.debug("%s: Detected task change for agent '%s' (previous task: '%s', current task: '%s').", 
                        func_name, agent_id, state.agent_last_task[agent_id], current_task_id)

            # Remove error registry entries for this agent that belong to previous tasks.
            keys_to_remove = [key for key in state.error_registry.keys() if key.startswith(f"{agent_id}:") and key != current_key]
            logger.debug("%s: Removing error registry entries for agent '%s': %s", func_name, agent_id, keys_to_remove)
            for key in keys_to_remove:
                del state.error_registry[key]
            
            # Initialize error count for the current task.
            state.error_registry[current_key] = 0
            logger.info("%s: Initialized error count for agent '%s' on task '%s'.", func_name, agent_id, current_task_id)
            
            # Update the last task for this agent.
            state.agent_last_task[agent_id] = current_task_id
            logger.debug("%s: Updated agent_last_task for agent '%s' to '%s'.", func_name, agent_id, current_task_id)
        else:
            # No previous task recorded; simply record the current task.
            state.agent_last_task[agent_id] = current_task_id
            logger.debug("%s: Recorded current task '%s' for agent '%s' (no previous task was found).", func_name, current_task_id, agent_id)

    def _update_error_registry_and_cache(self, state: RAGMiddlewareState, func_name: str) -> None:
        """
        Updates the error registry and in-memory cache based on the final response.
        
        Args:
            state (RAGMiddlewareState): The current middleware state.
            func_name (str): Name of the calling function (for logging purposes).
        """
        error_key = self._make_error_key(state.agent_id, state.task_id)
    
        # Update error registry.
        if state.response_type in [RagResponseType.ANSWERED, RagResponseType.FROM_CACHE]:
            state.error_registry[error_key] = 0
            logger.debug("%s: Reset error count for agent '%s', task '%s' because response type is '%s'.", 
                        func_name, state.agent_id, state.task_id, state.response_type)
        else:
            current_error_count = state.error_registry.get(error_key, 0)
            state.error_registry[error_key] = current_error_count + 1
            logger.info("%s: Incremented error registry for agent '%s', task '%s' to %d.",
                        func_name, state.agent_id, state.task_id, state.error_registry[error_key])
        
        # Update the cache.
        if state.response_type == RagResponseType.ANSWERED:
            # If in_memory_query_lookup is a dictionary, use:
            state.in_memory_query_lookup.add(state.query, state.response)
            logger.info("%s: Cached response for query: '%s'.", func_name, state.query)
        elif state.response_type == RagResponseType.FROM_CACHE:
            state.response_type = RagResponseType.ANSWERED
        else:
            logger.debug("%s: Response type '%s' is not cacheable; skipping cache update.", func_name, state.response_type)

    @staticmethod
    def _make_error_key(agent_id: str, task_id: str) -> str:
        """
        Constructs a unique key for the error registry based on the agent ID and task ID.

        Args:
            agent_id (str): The unique identifier of the agent.
            task_id (str): The unique identifier of the task.

        Returns:
            str: A string key in the format "agent_id:task_id" suitable for use in the error registry.
        """
        key = f"{agent_id}:{task_id}"
        logger.debug("Constructed error key: %s", key)
        return key

    def _invoke_agent(self, agent: BaseAgent, task_description: str, state: RAGMiddlewareState) -> None:
        """
        Private method to invoke an agent (RAG or Research) with a standardized input.

        Constructs the input for the agent using the current state, sets the task description,
        invokes the agent, and parses its output into RAGQueryOutput which is stored in the state.

        Args:
            agent (BaseAgent): The agent to invoke.
            task_description (str): The description for the current task.
            state (RAGMiddlewareState): The current workflow state.
        """
        func_name = "_invoke_agent"
        agent_input = RAGQueryInput(**state.model_dump(include=set(RAGQueryInput.model_fields.keys())))
        agent_input.current_task = Task(
            task_status=Status.NEW,
            description=task_description
        )
        logger.debug("%s: Constructed input: %s", func_name, agent_input)
        agent_output_raw = agent.invoke(agent_input.model_dump())
        logger.debug("%s: Raw output from agent: %s", func_name, agent_output_raw)
        state.rag_agent_output = RAGQueryOutput(**agent_output_raw)
        logger.debug("%s: Parsed agent output: %s", func_name, state.rag_agent_output)
