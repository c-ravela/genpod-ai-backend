"""
ReviewerGraph Class

Defines the state graph for the ReviewerAgent, handling code review workflows.
"""

from langgraph.graph import END, StateGraph

from agents.base.base_graph import BaseGraph
from agents.reviewer.reviewer_agent import ReviewerAgent
from agents.reviewer.reviewer_state import ReviewerState
from llms.llm import LLM
from utils.logs.logging_utils import logger


class ReviewerGraph(BaseGraph[ReviewerAgent]):
    """
    ReviewerGraph manages the workflow for the ReviewerAgent, defining the state
    graph and its transitions, including static code analysis and state updates.

    Attributes:
        agent_id (str): Unique identifier for the agent.
        agent_name (str): Name of the agent.
        llm (LLM): Language model for generating responses.
        persistance_db_path (str): Path to the database for graph persistence.
    """

    def __init__(
        self,
        graph_id: str,
        graph_name: str,
        agent_id: str,
        agent_name: str,
        llm: LLM,
        persistance_db_path: str
    ) -> None:
        """
        Initializes the ReviewerGraph with its nodes, agent, and persistence settings.

        Args:
            graph_id (str): Unique identifier for the graph.
            graph_name (str): Name of the graph.
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Name of the agent.
            llm (LLM): The language learning model used by the agent.
            persistance_db_path (str): Path to the database for graph persistence.
        """
        super().__init__(
            graph_id,
            graph_name, 
            ReviewerAgent(agent_id, agent_name, llm),
            persistance_db_path
        )

        logger.info(f"Initializing ReviewerGraph: {graph_name} with ID: {graph_id}")
        self.compile_graph_with_persistence()

    def define_graph(self) -> StateGraph:
        """
        Defines the workflow graph for the ReviewerAgent.

        Returns:
            StateGraph: The fully defined state graph.
        """
        logger.info(f"Defining the state graph for ReviewerAgent")
        reviewer_flow = StateGraph(ReviewerState)

        # nodes
        logger.info("Adding nodes to the ReviewerGraph")
        reviewer_flow.add_node(self.agent.entry_node_name, self.agent.entry_node)
        reviewer_flow.add_node(self.agent.static_code_analysis_node_name, self.agent.static_code_analysis_node)
        reviewer_flow.add_node(self.agent.update_state_node_name, self.agent.update_state)
        
        # edges
        logger.info("Defining edges for the ReviewerGraph")
        reviewer_flow.add_edge(self.agent.entry_node_name, self.agent.static_code_analysis_node_name)
        
        reviewer_flow.add_conditional_edges(
            self.agent.static_code_analysis_node_name,
            self.agent.router,
            {
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        reviewer_flow.add_edge(self.agent.update_state_node_name, END)

        # entry point
        logger.info("Setting entry point for the ReviewerGraph")
        reviewer_flow.set_entry_point(self.agent.entry_node_name)

        return reviewer_flow

    def get_current_state(self) -> ReviewerState:
        """
        Retrieves the current state of the graph.

        Returns:
            ReviewerState: The current state of the ReviewerAgent.
        """
        logger.info(f"Fetching current state for ReviewerGraph")
        return self.agent.state
