from dataclasses import dataclass
from os import getcwd, path
from typing import List

from agents.research._internal.research_mode_enum import (ResearchMode,
                                                          ResearchStage)
from agents.research._internal.research_node_enum import ResearchNodeEnum
from agents.research._internal.research_prompt import ResearchPrompts
from agents.research._internal.research_state import (ResearchOutput,
                                                      ResearchState)
from core.decorators import (handle_errors_and_reset, record_node,
                             route_on_errors)
from core.search import WebSearch
from core.workflow import BaseWorkFlow
from llms import LLM
from models import (GeneratedResponse, RagResponseType,
                    RelevanceEvaluationResponse, SourceSelectionResponse,
                    Status)
from utils.logger import logger
from utils.yaml_utils import read_yaml

SOURCE_URL_FILE_PATH = path.join(getcwd(), "agents", "research", "_internal", "research_urls.yaml")
MAX_REFINEMENT_ATTEMPTS = 3


@dataclass
class ResearchSource:
    """
    Represents a research source containing metadata about an information source.

    Attributes:
        name (str): The title or identifier of the source.
        url (str): The web link to the source.
        description (str): A brief summary of the source's content or purpose.
    """
    name: str
    url: str
    description: str


class ResearchWorkFlow(BaseWorkFlow[ResearchPrompts]):

    def __init__(self, agent_id: str, agent_name: str, llm: LLM):
        super().__init__(agent_id, agent_name, ResearchPrompts() , llm)

    @route_on_errors
    def router(self, state: ResearchState) -> str:
        """
        Routes the research process based on the current state.

        This method inspects the operational mode and current research stage from the provided
        state object and returns the corresponding research node as a string.

        Args:
            state (ResearchState): The current research state containing the operational mode and current stage.

        Returns:
            str: The string representation of the next research node.
        """
        logger.info("Routing research state: %s", state)
        
        if state.operational_mode == ResearchMode.RESEARCH:
            if state.current_mode_stage == ResearchStage.SOURCE_BASED_RESEARCH:
                node = str(ResearchNodeEnum.SOURCE_DRIVEN_RESEARCH)
                logger.debug("Mapping SOURCE_BASED_RESEARCH to %s", node)
                return node
            elif state.current_mode_stage == ResearchStage.OPEN_WEB_RESEARCH:
                node = str(ResearchNodeEnum.OPEN_WEB_RESEARCH)
                logger.debug("Mapping OPEN_WEB_RESEARCH to %s", node)
                return node
            elif state.current_mode_stage == ResearchStage.RESULTS_ASSESSMENT:
                node = str(ResearchNodeEnum.SEARCH_RESULTS_ASSESSMENT)
                logger.debug("Mapping RESULTS_ASSESSMENT to %s", node)
                return node
            elif state.current_mode_stage == ResearchStage.RESPONSE_GENERATION:
                node = str(ResearchNodeEnum.RESPONSE_GENERATION)
                logger.debug("Mapping RESPONSE_GENERATION to %s", node)
                return node
            elif state.current_mode_stage == ResearchStage.FINISHED:
                node = str(ResearchNodeEnum.EXIT)
                logger.debug("Mapping FINISHED to %s", node)
                return node
            else:
                logger.warning("Unknown research stage '%s'. Defaulting to EXIT.", state.current_mode_stage)
                return str(ResearchNodeEnum.EXIT)

        logger.info("Operational mode is not RESEARCH. Defaulting to EXIT.")
        return str(ResearchNodeEnum.EXIT)

    @record_node(ResearchNodeEnum.ENTRY)
    def entry_node(self, state: ResearchState) -> ResearchState:
        """
        Initializes and prepares the research state for the research workflow.

        This entry node function sets up the initial state based on the current task's status.
        If the current task is new, it resets response-related fields and sets the operational mode
        to active research with the initial stage set to source-guided exploration. Otherwise, it marks
        the operational mode as finished.

        Args:
            state (ResearchState): The current research state.

        Returns:
            ResearchState: The updated research state.

        Raises:
            Exception: Propagates any exceptions encountered during state initialization.
        """
        func_name = "entry_node"
        logger.info("Agent '%s': Entering %s", self.agent_name, func_name)

        try:
            if state.current_task.task_status == Status.NEW:
                logger.debug("Task status is NEW. Initializing state for active research.")
                state.response = ""
                state.response_type = ""
                state.metadata = {}
                state.operational_mode = ResearchMode.RESEARCH
                state.current_mode_stage = ResearchStage.SOURCE_BASED_RESEARCH
            else:
                logger.debug("Task status is not NEW. Marking research as finished.")
                state.operational_mode = ResearchMode.FINISHED
        except Exception as e:
            logger.error(
                "Agent '%s': Function '%s': Error in entry_node: %s",
                self.agent_name,
                func_name,
                e,
                exc_info=True
            )
            raise

        logger.info("Agent '%s': Exiting %s with state: %s", self.agent_name, func_name, state)
        return state

    @record_node(ResearchNodeEnum.SOURCE_DRIVEN_RESEARCH)
    @handle_errors_and_reset
    def execute_source_based_research_node(self, state: ResearchState) -> ResearchState:
        """
        Performs research using predefined sources.

        This method loads predefined generate_repsonesources from configuration (YAML) and uses an LLM prompt to select the most relevant
        sources for the given query. If no sources are available or none are selected, it switches the research stage to 
        OPEN_WEB_RESEARCH. Otherwise, it updates the research state with the selected sources' evaluation details and 
        moves to the RESULTS_ASSESSMENT stage.

        Args:
            state (ResearchState): The current research state containing query and task details.

        Returns:
            ResearchState: The updated research state reflecting the outcome of the source-based research step.
        """
        logger.info("Starting source-based research.")

        sources = self._load_source()
        if len(sources) == 0:
            logger.warning("No predefined sources found. Switching to open web research.")
            state.current_mode_stage = ResearchStage.OPEN_WEB_RESEARCH
            return state

        source_list_str = "\n".join(f"{source.name}: {source.description}" for source in sources)

        llm_response = self.invoke_with_pydantic_model(
            self.prompts.source_selection_prompt,
            {"source_list": source_list_str, "query": state.query},
            SourceSelectionResponse
        )

        selected_source_names = llm_response.response.source_names
        state.source_evaluation_details = llm_response.response.details

        selected_sources = [source for source in sources if source.name in selected_source_names]
        if len(selected_sources) == 0:
            logger.warning("No sources selected by the LLM. Switching to open web research.")
            state.current_mode_stage = ResearchStage.OPEN_WEB_RESEARCH
            return state

        # TODO:
        # call search api on those sources and send response for evaluaiton
        # holds the selected sources in state so that we 
        # flow loops back here due to irrelevant response then 
        # this node shouldnt  call llm to select source again
        # empty out the suggestions
        state.current_mode_stage = ResearchStage.OPEN_WEB_RESEARCH # Need to be RESULTS_ASSEMENT once logic was inplace
        logger.info("Source-based research completed successfully. Moving to results assessment stage.")
        return state  

    @record_node(ResearchNodeEnum.OPEN_WEB_RESEARCH)
    @handle_errors_and_reset
    def perform_open_web_research_node(self, state: ResearchState) -> ResearchState:
        """
        Executes an open web search to gather general information for the provided query and prepares the data for evaluation.

        This method uses the Google search engine via the WebSearch wrapper to retrieve search results for the query
        contained in the state. The search results are formatted as a string (combining titles and snippets) for logging
        or further evaluation. The research state is then updated to transition to the RESULTS_ASSESSMENT stage.

        Args:
            state (ResearchState): The current research state, which includes the query and other relevant data.

        Returns:
            ResearchState: The updated research state after performing open web research.

        Raises:
            RuntimeError: If the web search operation fails.
        """
        logger.info("Performing open web research for query: '%s'", state.query)

        web_search = WebSearch()
        search_result = web_search.search(state.query)
        state.search_results = search_result

        search_result_str = "\n".join(
            f"{result.title}: {result.snippet}" for result in search_result.results
        )
        logger.debug("Open web search results:\n%s", search_result_str)

        state.current_mode_stage = ResearchStage.RESULTS_ASSESSMENT
        logger.info("Open web research completed. Transitioning to RESULTS_ASSESSMENT stage.")
        return state

    @record_node(ResearchNodeEnum.SEARCH_RESULTS_ASSESSMENT)
    @handle_errors_and_reset
    def assess_response_relevance_node(self, state: ResearchState) -> ResearchState:
        """
        Evaluates the relevance of the generated response against the query and updates the research state accordingly.

        This method uses an LLM-based prompt to determine if the generated response adequately addresses the query.
        If the response is deemed irrelevant, it reverts the research stage based on the last executed node—either 
        OPEN_WEB_RESEARCH or SOURCE_BASED_RESEARCH—and updates the query with a refined version provided by the LLM.
        If the response is relevant, it transitions the research state to the RESPONSE_GENERATION stage.

        Args:
            state (ResearchState): The current research state, including the query and the generated response.

        Returns:
            ResearchState: The updated research state after evaluating the response relevance.
        """
        logger.info("Assessing response relevance for query: '%s'", state.query)

        search_result_str = "\n".join(
            f"{result.title}: {result.snippet}" for result in state.search_results.results
        )

        llm_response = self.invoke_with_pydantic_model(
            self.prompts.relevance_check_prompt,
            {"query": state.query, "response": search_result_str},
            RelevanceEvaluationResponse
        )
        is_response_relevant = llm_response.response.is_relevant
        logger.debug("LLM evaluated response relevance: %s", is_response_relevant)

        if not is_response_relevant:
            logger.info("Response deemed irrelevant. Adjusting research state based on last node.")
            if state.last_node == ResearchNodeEnum.OPEN_WEB_RESEARCH:
                state.current_mode_stage = ResearchStage.OPEN_WEB_RESEARCH
                logger.debug("Resetting stage to OPEN_WEB_RESEARCH based on last node.")
            elif state.last_node == ResearchNodeEnum.SOURCE_DRIVEN_RESEARCH:
                state.current_mode_stage = ResearchStage.SOURCE_BASED_RESEARCH
                logger.debug("Resetting stage to SOURCE_BASED_RESEARCH based on last node.")
            else:
                logger.warning("Unrecognized last node '%s'. Defaulting to OPEN_WEB_RESEARCH.", state.last_node)
                state.current_mode_stage = ResearchStage.OPEN_WEB_RESEARCH

            current_attempts = state.refinement_attempts
            if current_attempts < MAX_REFINEMENT_ATTEMPTS:
                state.refinement_attempts = current_attempts + 1
                state.query = llm_response.response.refined_query
                logger.info("Updated query with refined query: '%s' (refinement attempt %d)", 
                            state.query, state.refinement_attempts)
            else:
                logger.warning("Maximum refinement attempts (%d) reached; proceeding with current query.", MAX_REFINEMENT_ATTEMPTS)
                state.current_mode_stage = ResearchStage.RESPONSE_GENERATION
                state.response_details = llm_response.response.details

            return state

        state.response_details = llm_response.response.details
        state.current_mode_stage = ResearchStage.RESPONSE_GENERATION
        logger.info("Response is relevant. Transitioning to RESPONSE_GENERATION stage.")
        return state

    @record_node(ResearchNodeEnum.RESPONSE_GENERATION)
    @handle_errors_and_reset
    def generate_response_node(self, state: ResearchState) -> ResearchState:
        """
        Generates a final response by synthesizing the provided query and web search results.

        This method invokes an LLM prompt to produce a clear and concise response based on the input query and the 
        web search results. The search results are first formatted into a human-readable string before being passed to the prompt.
        Once the response is generated, the research state is updated with the new response, the response type is set as ANSWERED,
        and the research stage is marked as FINISHED.

        Args:
            state (ResearchState): The current research state, which includes the query and web search results.

        Returns:
            ResearchState: The updated research state containing the generated response and related metadata.
        """
        logger.info("Generating final response for query: '%s'", state.query)

        results_str = "\n".join(
            f"{result.title}: {result.snippet}" for result in state.search_results.results
        )
        logger.debug("Formatted search results for prompt:\n%s", results_str)

        llm_response = self.invoke_with_pydantic_model(
            self.prompts.generate_response_prompt,
            {"query": state.query, "results": results_str},
            GeneratedResponse
        )

        state.response = llm_response.response.content
        state.response_type = RagResponseType.ANSWERED
        state.current_mode_stage = ResearchStage.FINISHED

        logger.info("Generated response: '%s'", state.response)
        return state

    @record_node(ResearchNodeEnum.EXIT)
    def exit_node(self, state: ResearchState) -> ResearchOutput:
        """
        Finalizes the research process and prepares the final output.

        This method checks the current operational mode and research stage. If the research is still active 
        and the stage is marked as FINISHED, the task status is updated to DONE. Otherwise, appropriate 
        warnings are logged. Finally, the finalized research output is returned.

        Args:
            state (ResearchState): The current research state containing task status, operational mode, and stage information.

        Returns:
            ResearchOutput: The finalized research output after processing the exit node.
        """
        func_name = "exit_node"

        if state.operational_mode == ResearchMode.RESEARCH:
            if state.current_mode_stage == ResearchStage.FINISHED:
                state.current_task.task_status = Status.DONE
                logger.info("Exiting research: research completed. Task marked as DONE.")
            else:
                logger.warning("Exiting research: current mode stage '%s' is not FINISHED.", state.current_mode_stage)
        else:
            logger.warning("Exiting research: operational mode is '%s' (expected RESEARCH).", state.operational_mode)

        logger.info("Exit node '%s' completed.", func_name)
        return state

    @staticmethod
    def _load_source() -> List[ResearchSource]:
        """
        Loads research sources from a YAML file and returns a list of ResearchSource objects.

        Returns:
            List[ResearchSource]: A list of research sources loaded from the YAML file.

        Raises:
            Exception: If an error occurs while reading or processing the YAML file.
        """
        try:
            logger.info("Loading research sources from YAML file: %s", SOURCE_URL_FILE_PATH)
            raw_data = read_yaml(SOURCE_URL_FILE_PATH)
            sources_data = raw_data.get('sources') or []

            sources = [ResearchSource(**source) for source in sources_data]
            logger.info("Successfully loaded %d research sources.", len(sources))
            return sources
        except Exception as e:
            logger.error("Failed to load research sources: %s", str(e), exc_info=True)
            raise
