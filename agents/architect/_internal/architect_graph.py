"""
Architect Graph Module

This module defines the `ArchitectGraph` class, responsible for defining and managing the state graph 
for the Architect agent. The state graph determines the control flow between different states of the 
Architect agent. This class provides methods to define the graph, add nodes and edges, and designate 
the entry and finish points, all with integrated logging for better traceability.
"""

from langgraph.graph import StateGraph

from agents.architect._internal.architect_node_enum import ArchitectNodeEnum
from agents.architect._internal.architect_state import *
from agents.architect._internal.architect_work_flow import ArchitectWorkFlow
from core.graph import BaseGraph
from utils.logs.logging_utils import logger


class ArchitectGraph(BaseGraph[ArchitectWorkFlow]):
    """
    ArchitectGraph defines the state graph for the Architect agent.

    This class builds a StateGraph using the Architect agent's workflow methods. 
    It adds nodes representing various stages (e.g., ENTRY, GENERATE_REQUIREMENTS, EXTRACT_TASKS, etc.),
    connects them with conditional edges based on the router function, and sets the entry and finish points.

    Attributes:
        work_flow (ArchitectWorkFlow): The workflow instance controlling the state transitions.
        recursion_limit (int): The maximum recursion depth for state transitions.
        persistence_db_path (str): Path to the database used for persistence.
    """

    def __init__(
        self,
        work_flow: ArchitectWorkFlow, 
        recursion_limit: int,
        persistence_db_path: str
    ):
        """
        Initializes the ArchitectGraph with the specified workflow, recursion limit, and persistence database path.

        Args:
            work_flow (ArchitectWorkFlow): The workflow associated with this graph.
            recursion_limit (int): Maximum recursion depth for processing. Must be a positive integer.
            persistence_db_path (str): Path to the persistence database.
        
        Raises:
            ValueError: If recursion_limit is not positive or persistence_db_path is invalid.
        """
        logger.info("Initializing ArchitectGraph with recursion_limit=%s and persistence_db_path=%s",
                    recursion_limit, persistence_db_path)
        super().__init__(work_flow, recursion_limit, persistence_db_path)

    def define_graph(self) -> StateGraph:
        """
        Defines and returns the state graph for the Architect agent.

        The graph is built with the following structure:
          - Nodes are added corresponding to key workflow stages (e.g., ENTRY, GENERATE_REQUIREMENTS,
            EXTRACT_TASKS, SAVE_REQUIREMENTS, GATHER_PROJECT_DETAILS, EXIT).
          - Conditional edges are established between nodes based on the router function from the workflow.
          - The entry point is set to the ENTRY node and the finish point to the EXIT node.

        Returns:
            StateGraph: The fully defined state graph.
        """
        logger.info("Defining state graph for Architect agent.")

        architect_work_flow_graph = StateGraph(ArchitectState, input=ArchitectInput, output=ArchitectOutput)
        
        # Adding nodes with logging.
        logger.info("Adding nodes to the state graph.")
        architect_work_flow_graph.add_node(
            str(ArchitectNodeEnum.ENTRY),
            self.work_flow.entry_node
        )
        logger.debug("Added node: %s", ArchitectNodeEnum.ENTRY)
        architect_work_flow_graph.add_node(
            str(ArchitectNodeEnum.GENERATE_REQUIREMENTS),
            self.work_flow.generate_requirements_document_node
        )
        logger.debug("Added node: %s", ArchitectNodeEnum.GENERATE_REQUIREMENTS)
        architect_work_flow_graph.add_node(
            str(ArchitectNodeEnum.EXTRACT_TASKS),
            self.work_flow.extract_tasks_node
        )
        logger.debug("Added node: %s", ArchitectNodeEnum.EXTRACT_TASKS)
        architect_work_flow_graph.add_node(
            str(ArchitectNodeEnum.SAVE_REQUIREMENTS),
            self.work_flow.save_requirements_document_node
        )
        logger.debug("Added node: %s", ArchitectNodeEnum.SAVE_REQUIREMENTS)
        architect_work_flow_graph.add_node(
            str(ArchitectNodeEnum.GATHER_PROJECT_DETAILS),
            self.work_flow.gather_project_details_node
        )
        logger.debug("Added node: %s", ArchitectNodeEnum.GATHER_PROJECT_DETAILS)
        architect_work_flow_graph.add_node(
            str(ArchitectNodeEnum.EXIT),
            self.work_flow.exit_node
        )
        logger.debug("Added node: %s", ArchitectNodeEnum.EXIT)

        # Adding conditional edges with logging.
        logger.info("Adding conditional edges to the state graph.")
        architect_work_flow_graph.add_conditional_edges(
            str(ArchitectNodeEnum.ENTRY),
            self.work_flow.router, {
                str(ArchitectNodeEnum.GENERATE_REQUIREMENTS): str(ArchitectNodeEnum.GENERATE_REQUIREMENTS),
                str(ArchitectNodeEnum.EXIT): str(ArchitectNodeEnum.EXIT)
            }
        )
        logger.debug("Added conditional edges from node: %s", ArchitectNodeEnum.ENTRY)
        architect_work_flow_graph.add_conditional_edges(
            str(ArchitectNodeEnum.GENERATE_REQUIREMENTS),
            self.work_flow.router, {
                str(ArchitectNodeEnum.EXTRACT_TASKS): str(ArchitectNodeEnum.EXTRACT_TASKS),
                str(ArchitectNodeEnum.EXIT): str(ArchitectNodeEnum.EXIT)
            }
        )
        logger.debug("Added conditional edges from node: %s", ArchitectNodeEnum.GENERATE_REQUIREMENTS)
        architect_work_flow_graph.add_conditional_edges(
            str(ArchitectNodeEnum.EXTRACT_TASKS),
            self.work_flow.router, {
                str(ArchitectNodeEnum.SAVE_REQUIREMENTS): str(ArchitectNodeEnum.SAVE_REQUIREMENTS),
                str(ArchitectNodeEnum.EXIT): str(ArchitectNodeEnum.EXIT)
            }
        )
        logger.debug("Added conditional edges from node: %s", ArchitectNodeEnum.EXTRACT_TASKS)
        architect_work_flow_graph.add_conditional_edges(
            str(ArchitectNodeEnum.SAVE_REQUIREMENTS),
            self.work_flow.router, {
                str(ArchitectNodeEnum.GATHER_PROJECT_DETAILS): str(ArchitectNodeEnum.GATHER_PROJECT_DETAILS),
                str(ArchitectNodeEnum.EXIT): str(ArchitectNodeEnum.EXIT)
            }
        )
        logger.debug("Added conditional edges from node: %s", ArchitectNodeEnum.SAVE_REQUIREMENTS)
        architect_work_flow_graph.add_conditional_edges(
            str(ArchitectNodeEnum.GATHER_PROJECT_DETAILS),
            self.work_flow.router, {
                str(ArchitectNodeEnum.EXIT): str(ArchitectNodeEnum.EXIT)
            }
        )
        logger.debug("Added conditional edges from node: %s", ArchitectNodeEnum.GATHER_PROJECT_DETAILS)

        # Set the entry and finish points of the graph.
        logger.info("Setting entry and finish points of the state graph.")
        architect_work_flow_graph.set_entry_point(str(ArchitectNodeEnum.ENTRY))
        architect_work_flow_graph.set_finish_point(str(ArchitectNodeEnum.EXIT))

        logger.info("State graph defined successfully.")
        return architect_work_flow_graph
