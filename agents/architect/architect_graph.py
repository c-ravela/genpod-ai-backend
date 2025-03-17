"""
Architect Graph Module

This module defines the `ArchitectGraph` class, responsible for defining
and managing the state graph for the Architect agent. The state graph 
determines the flow of control between different states of the Architect agent.
This class provides methods to define the graph, add nodes and edges, 
and designate the entry point, all with integrated logging for better traceability.
"""
from langgraph.graph import END, StateGraph

from agents.architect.architect_agent import ArchitectAgent
from agents.architect.architect_state import ArchitectState
from agents.base.base_graph import BaseGraph
from llms.llm import LLM
from utils.logs.logging_utils import logger


class ArchitectGraph(BaseGraph[ArchitectAgent]):
    """
    ArchitectGraph Class

    This class is responsible for defining and managing the state graph for the 
    Architect agent. The state graph is a control flow diagram that dictates the 
    transitions between different states of the Architect agent. This class 
    provides methods to define the graph, add nodes and edges, and designate 
    the entry point, all with integrated logging for better traceability.
    """

    def __init__(
        self,
        graph_id: str,
        graph_name: str,
        agent_id: str,
        agent_name: str,
        llm: LLM,
        persistence_db_path: str
    ) -> None:
        """
        Constructor for the ArchitectGraph class.

        Initializes the ArchitectGraph with a specified Language Learning Model (LLM) 
        and sets up the state graph with persistence capabilities.

        Args:
            graph_id (str): Unique identifier for the graph.
            graph_name (str): Human-readable name for the graph.
            agent_id (str): Unique identifier for the Architect agent.
            agent_name (str): Human-readable name for the Architect agent.
            llm (LLM): Language Learning Model instance used by the agent.
            persistence_db_path (str): Path to the persistence database.
        """
        logger.info(
            f"Initializing ArchitectGraph with graph_id='{graph_id}', "
            f"graph_name='{graph_name}', agent_id='{agent_id}', "
            f"agent_name='{agent_name}'."
        )
        super().__init__(
            graph_id,
            graph_name,
            ArchitectAgent(agent_id, agent_name, llm),
            persistence_db_path
        )
        self.compile_graph_with_persistence()
        logger.debug("ArchitectGraph initialized and compiled with persistence.")

    def define_graph(self) -> StateGraph:
        """
        Defines the state graph for the Architect agent.

        The graph includes nodes representing different states of the agent and 
        edges representing possible transitions between states. This method returns 
        the compiled state graph.

        Returns:
            StateGraph: The compiled state graph for the Architect agent.
        """
        logger.info("Defining the state graph for the Architect agent.")
        architect_flow = StateGraph(ArchitectState)

        # node
        logger.debug("Adding nodes to the state graph.")
        architect_flow.add_node(
            self.agent.entry_node_name,
            self.agent.entry_node
        )
        architect_flow.add_node(
            self.agent.requirements_node_name,
            self.agent.requirements_node
        )
        architect_flow.add_node(
            self.agent.additional_info_node_name,
            self.agent.additional_information_node
        )
        architect_flow.add_node(
            self.agent.write_requirements_node_name,
            self.agent.write_requirements_node
        )
        architect_flow.add_node(
            self.agent.tasks_separation_node_name,
            self.agent.tasks_separation_node
        )
        architect_flow.add_node(
            self.agent.project_details_node_name,
            self.agent.project_details_node
        )
        architect_flow.add_node(
            self.agent.update_state_node_name,
            self.agent.update_state
        )

        # edges
        logger.debug("Adding conditional edges to the state graph.")
        architect_flow.add_conditional_edges(
            self.agent.entry_node_name,
            self.agent.router, 
            {
                self.agent.requirements_node_name: self.agent.requirements_node_name,
                self.agent.additional_info_node_name: self.agent.additional_info_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name,
            }
        )
        
        architect_flow.add_conditional_edges(
            self.agent.requirements_node_name,
            self.agent.router,
            {
                self.agent.requirements_node_name: self.agent.requirements_node_name,
                self.agent.write_requirements_node_name: self.agent.write_requirements_node_name,
                self.agent.tasks_separation_node_name: self.agent.tasks_separation_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        architect_flow.add_conditional_edges(
            self.agent.additional_info_node_name,
            self.agent.router,
            {   
                self.agent.additional_info_node_name: self.agent.additional_info_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        architect_flow.add_conditional_edges(
            self.agent.write_requirements_node_name,
            self.agent.router, 
            {
                self.agent.tasks_separation_node_name: self.agent.tasks_separation_node_name,
                self.agent.requirements_node_name:self.agent.requirements_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        architect_flow.add_conditional_edges(
            self.agent.tasks_separation_node_name,
            self.agent.router, 
            {
                self.agent.tasks_separation_node_name: self.agent.tasks_separation_node_name,
                self.agent.project_details_node_name: self.agent.project_details_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        architect_flow.add_conditional_edges(
            self.agent.project_details_node_name,
            self.agent.router, 
            {
                self.agent.project_details_node_name: self.agent.project_details_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        architect_flow.add_edge(self.agent.update_state_node_name, END)
        logger.debug("Final edge to END added.")

        # entry point
        architect_flow.set_entry_point(self.agent.entry_node_name)
        logger.info(f"Entry point set to '{self.agent.entry_node_name}'.")

        logger.info("State graph definition complete.")
        return architect_flow

    def get_current_state(self) -> ArchitectState:
        """
        Retrieves the current state of the Architect agent.

        Returns:
            ArchitectState: The current state of the Architect agent.
        """
        logger.info("Fetching the current state of the Architect agent.")
        current_state = self.agent.state
        logger.debug(f"Current state retrieved: {current_state}")
        return current_state
