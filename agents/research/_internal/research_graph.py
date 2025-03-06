from langgraph.graph import StateGraph

from agents.research._internal.research_node_enum import ResearchNodeEnum
from agents.research._internal.research_state import (ResearchInput,
                                                      ResearchOutput,
                                                      ResearchState)
from agents.research._internal.research_work_flow import ResearchWorkFlow
from core.graph import BaseGraph
from utils.logs.logging_utils import logger


class ResearchGraph(BaseGraph[ResearchWorkFlow]):
    """
    Represents the state graph for the Research Workflow.

    This graph defines the sequence of nodes and conditional edges that govern the execution
    flow of the research process. It integrates the research workflow nodes into a state graph
    that accepts a ResearchInput, processes a ResearchState, and produces a ResearchOutput.

    Attributes:
        work_flow (ResearchWorkFlow): The research workflow instance containing node definitions.
        recursion_limit (int): The maximum recursion depth allowed for the graph.
        persistence_db_path (str): The file path to the persistence database for the graph state.
    """

    def __init__(self, work_flow: ResearchWorkFlow, recursion_limit: int, persistence_db_path: str):
        super().__init__(work_flow, recursion_limit, persistence_db_path)
        logger.info("Initialized ResearchGraph with recursion_limit=%d and persistence_db_path='%s'.",
                    recursion_limit, persistence_db_path)

    def define_graph(self) -> StateGraph:
        """
        Constructs and returns a StateGraph for the research workflow by integrating the workflow's nodes
        and defining the transitions between them.

        Returns:
            StateGraph: The constructed state graph representing the research workflow.
        """
        logger.info("Defining research workflow graph.")
        research_work_flow_graph = StateGraph(ResearchState, input=ResearchInput, output=ResearchOutput)

        nodes = {
            ResearchNodeEnum.ENTRY: self.work_flow.entry_node,
            ResearchNodeEnum.SOURCE_DRIVEN_RESEARCH: self.work_flow.execute_source_based_research_node,
            ResearchNodeEnum.OPEN_WEB_RESEARCH: self.work_flow.perform_open_web_research_node,
            ResearchNodeEnum.SEARCH_RESULTS_ASSESSMENT: self.work_flow.assess_response_relevance_node,
            ResearchNodeEnum.RESPONSE_GENERATION: self.work_flow.generate_response_node,
            ResearchNodeEnum.EXIT: self.work_flow.exit_node
        }

        for node_name, node_function in nodes.items():
            research_work_flow_graph.add_node(str(node_name), node_function)
            logger.debug("Added node: %s", node_name)

        research_work_flow_graph.add_conditional_edges(
            str(ResearchNodeEnum.ENTRY),
            self.work_flow.router,
            {
                str(ResearchNodeEnum.SOURCE_DRIVEN_RESEARCH): str(ResearchNodeEnum.SOURCE_DRIVEN_RESEARCH),
                str(ResearchNodeEnum.EXIT): str(ResearchNodeEnum.EXIT)
            }
        )
        logger.debug("Added conditional edges from ENTRY node.")

        research_work_flow_graph.add_conditional_edges(
            str(ResearchNodeEnum.SOURCE_DRIVEN_RESEARCH),
            self.work_flow.router,
            {
                str(ResearchNodeEnum.SEARCH_RESULTS_ASSESSMENT): str(ResearchNodeEnum.SEARCH_RESULTS_ASSESSMENT),
                str(ResearchNodeEnum.OPEN_WEB_RESEARCH): str(ResearchNodeEnum.OPEN_WEB_RESEARCH)
            }
        )
        logger.debug("Added conditional edges from SOURCE_DRIVEN_RESEARCH node.")

        research_work_flow_graph.add_edge(
            str(ResearchNodeEnum.OPEN_WEB_RESEARCH),
            str(ResearchNodeEnum.SEARCH_RESULTS_ASSESSMENT),
        )
        logger.debug("Added edge from OPEN_WEB_RESEARCH to SEARCH_RESULTS_ASSESSMENT.")

        research_work_flow_graph.add_conditional_edges(
            str(ResearchNodeEnum.SEARCH_RESULTS_ASSESSMENT),
            self.work_flow.router,
            {
                str(ResearchNodeEnum.OPEN_WEB_RESEARCH): str(ResearchNodeEnum.OPEN_WEB_RESEARCH),
                str(ResearchNodeEnum.SOURCE_DRIVEN_RESEARCH): str(ResearchNodeEnum.SOURCE_DRIVEN_RESEARCH),
                str(ResearchNodeEnum.RESPONSE_GENERATION): str(ResearchNodeEnum.RESPONSE_GENERATION)
            }
        )
        logger.debug("Added conditional edges from SEARCH_RESULTS_ASSESSMENT node.")

        research_work_flow_graph.add_edge(
            str(ResearchNodeEnum.RESPONSE_GENERATION),
            str(ResearchNodeEnum.EXIT),
        )
        logger.debug("Added edge from RESPONSE_GENERATION to EXIT.")

        research_work_flow_graph.set_entry_point(str(ResearchNodeEnum.ENTRY))
        research_work_flow_graph.set_finish_point(str(ResearchNodeEnum.EXIT))
        logger.info("Set entry point to '%s' and finish point to '%s'.",
                    ResearchNodeEnum.ENTRY, ResearchNodeEnum.EXIT)

        logger.info("Research workflow graph defined successfully.")
        return research_work_flow_graph
