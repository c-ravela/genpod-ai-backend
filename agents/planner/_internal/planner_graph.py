from langgraph.graph import StateGraph

from agents.planner._internal.planner_node_enum import PlannerNodeEnum
from agents.planner._internal.planner_state import (PlannerInput,
                                                    PlannerOutput,
                                                    PlannerState)
from agents.planner._internal.planner_work_flow import PlannerWorkFlow
from core.graph import BaseGraph
from utils.logger import logger


class PlannerGraph(BaseGraph[PlannerWorkFlow]):
    """
    Graph representation for the planner workflow.

    This class defines the nodes and edges that constitute the planner's execution flow.
    It builds a state graph using the provided PlannerWorkFlow instance and leverages
    PlannerState, PlannerInput, and PlannerOutput to manage the flow of operations.
    """

    def __init__(self, work_flow: PlannerWorkFlow, recursion_limit: int, persistence_db_path: str):
        """
        Initialize the PlannerGraph with a workflow, recursion limit, and persistence database path.

        Args:
            work_flow (PlannerWorkFlow): The workflow instance containing the planning nodes.
            recursion_limit (int): The maximum allowed recursion depth for the graph.
            persistence_db_path (str): The file path for the persistence database to store the graph state.
        """
        logger.debug(
            "Initializing PlannerGraph with recursion_limit: %d and persistence_db_path: %s",
            recursion_limit, persistence_db_path
        )
        super().__init__(work_flow, recursion_limit, persistence_db_path)

    def define_graph(self):
        """
        Construct and return the state graph representing the planner workflow.

        This method builds the graph by:
          - Creating a StateGraph using PlannerState, PlannerInput, and PlannerOutput.
          - Adding nodes corresponding to each planning stage.
          - Adding conditional edges from the ENTRY node based on the router function.
          - Defining direct edges between key nodes to set the workflow order.
          - Setting the entry and finish points of the graph.

        Returns:
            The constructed state graph representing the complete planner workflow.
        """
        logger.debug("Defining the planner state graph...")
        planner_work_flow = StateGraph(PlannerState, input=PlannerInput, output=PlannerOutput)
        logger.debug("Initialized StateGraph with PlannerState, PlannerInput, and PlannerOutput.")

        nodes = {
            PlannerNodeEnum.ENTRY: self.work_flow.entry_node,
            PlannerNodeEnum.TASK_DELIVERABLE_BREAKDOWN: self.work_flow.task_breakdown_node,
            PlannerNodeEnum.REQUIREMENTS_ANALYSIS: self.work_flow.requirements_analyzer_node,
            PlannerNodeEnum.TASK_WORKPACKAGE_UPDATE: self.work_flow.task_workpackage_update_node,
            PlannerNodeEnum.ISSUE_BREAKDOWN: self.work_flow.issues_preparation_node,
            PlannerNodeEnum.ISSUE_WORKPACKAGE_UPDATE: self.work_flow.issue_workpackage_update_node,
            PlannerNodeEnum.EXIT: self.work_flow.exit_node,
        }
        for node_name, node_function in nodes.items():
            planner_work_flow.add_node(str(node_name), node_function)
            logger.debug("Added node: %s", node_name)

        conditional_edges = {
            str(PlannerNodeEnum.TASK_DELIVERABLE_BREAKDOWN): str(PlannerNodeEnum.TASK_DELIVERABLE_BREAKDOWN),
            str(PlannerNodeEnum.TASK_WORKPACKAGE_UPDATE): str(PlannerNodeEnum.TASK_WORKPACKAGE_UPDATE),
            str(PlannerNodeEnum.ISSUE_BREAKDOWN): str(PlannerNodeEnum.ISSUE_BREAKDOWN),
            str(PlannerNodeEnum.ISSUE_WORKPACKAGE_UPDATE): str(PlannerNodeEnum.ISSUE_WORKPACKAGE_UPDATE),
            str(PlannerNodeEnum.EXIT): str(PlannerNodeEnum.EXIT)
        }
        planner_work_flow.add_conditional_edges(
            str(PlannerNodeEnum.ENTRY),
            self.work_flow.router,
            conditional_edges
        )
        logger.debug("Added conditional edges from ENTRY node using the router function.")

        planner_work_flow.add_edge(
            str(PlannerNodeEnum.TASK_DELIVERABLE_BREAKDOWN),
            str(PlannerNodeEnum.REQUIREMENTS_ANALYSIS)
        )
        logger.debug("Added edge from TASK_DELIVERABLE_BREAKDOWN to REQUIREMENTS_ANALYSIS.")

        planner_work_flow.add_edge(
            str(PlannerNodeEnum.REQUIREMENTS_ANALYSIS),
            str(PlannerNodeEnum.EXIT)
        )
        logger.debug("Added edge from REQUIREMENTS_ANALYSIS to EXIT.")

        planner_work_flow.add_edge(
            str(PlannerNodeEnum.ISSUE_BREAKDOWN),
            str(PlannerNodeEnum.EXIT)
        )
        logger.debug("Added edge from ISSUE_BREAKDOWN to EXIT.")

        planner_work_flow.add_edge(
            str(PlannerNodeEnum.TASK_WORKPACKAGE_UPDATE),
            str(PlannerNodeEnum.EXIT)
        )
        logger.debug("Added edge from TASK_WORKPACKAGE_UPDATE to EXIT.")

        planner_work_flow.add_edge(
            str(PlannerNodeEnum.ISSUE_WORKPACKAGE_UPDATE),
            str(PlannerNodeEnum.EXIT)
        )
        logger.debug("Added edge from ISSUE_WORKPACKAGE_UPDATE to EXIT.")

        planner_work_flow.set_entry_point(str(PlannerNodeEnum.ENTRY))
        logger.debug("Set graph entry point to: %s", str(PlannerNodeEnum.ENTRY))
        planner_work_flow.set_finish_point(str(PlannerNodeEnum.EXIT))
        logger.debug("Set graph finish point to: %s", str(PlannerNodeEnum.EXIT))

        logger.info("Planner graph defined successfully with nodes: %s", list(nodes.keys()))
        return planner_work_flow
