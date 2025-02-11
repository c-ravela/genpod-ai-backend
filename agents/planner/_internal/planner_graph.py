from langgraph.graph import END, StateGraph

from agents.planner._internal.planner_node_enum import PlannerNodeEnum
from agents.planner._internal.planner_state import (PlannerInput,
                                                    PlannerOutput,
                                                    PlannerState)
from agents.planner._internal.planner_work_flow import PlannerWorkFlow
from core.graph import BaseGraph
from utils.logs.logging_utils import logger


class PlannerGraph(BaseGraph[PlannerWorkFlow]):
    """
    Graph representation for the planner workflow.

    This class encapsulates the nodes and edges that define the planner's execution flow.
    It constructs a state graph using the provided PlannerWorkFlow instance and leverages
    PlannerState, PlannerInput, and PlannerOutput to manage the flow of operations.
    """

    def __init__(
        self,
        work_flow: PlannerWorkFlow,
        recursion_limit: int,
        persistence_db_path: str
    ):
        """
        Initialize the PlannerGraph.

        Args:
            work_flow (PlannerWorkFlow): The workflow instance containing the planning nodes.
            recursion_limit (int): The maximum depth of recursion allowed for the graph.
            persistence_db_path (str): Path to the persistence database for storing graph state.
        """
        logger.debug(
            "Initializing PlannerGraph with recursion_limit: %d and persistence_db_path: %s",
            recursion_limit,
            persistence_db_path
        )
        super().__init__(work_flow, recursion_limit, persistence_db_path)

    def define_graph(self):
        logger.debug("Defining planner state graph...")
        planner_work_flow = StateGraph(PlannerState, input=PlannerInput, output=PlannerOutput)
        logger.debug("Initialized StateGraph with PlannerState, PlannerInput, and PlannerOutput.")

        nodes = {
            str(PlannerNodeEnum.ENTRY): self.work_flow.entry_node,
            str(PlannerNodeEnum.TASK_BREAKDOWN): self.work_flow.task_breakdown_node,
            str(PlannerNodeEnum.REQUIREMENTS_ANALYZER): self.work_flow.requirements_analyzer_node,
            str(PlannerNodeEnum.ISSUE_BREAKDOWN): self.work_flow.issues_preparation_node,
            str(PlannerNodeEnum.EXIT): self.work_flow.exit_node,
        }
        for node_name, node_function in nodes.items():
            planner_work_flow.add_node(node_name, node_function)
            logger.debug("Added node: %s", node_name)

        conditional_edges = {
            str(PlannerNodeEnum.TASK_BREAKDOWN): str(PlannerNodeEnum.TASK_BREAKDOWN),
            str(PlannerNodeEnum.ISSUE_BREAKDOWN): str(PlannerNodeEnum.ISSUE_BREAKDOWN),
            str(PlannerNodeEnum.EXIT): str(PlannerNodeEnum.EXIT)
        }
        planner_work_flow.add_conditional_edges(
            str(PlannerNodeEnum.ENTRY),
            self.work_flow.router,
            conditional_edges
        )
        logger.debug("Added conditional edges from ENTRY node using router.")

        planner_work_flow.add_edge(
            str(PlannerNodeEnum.TASK_BREAKDOWN),
            str(PlannerNodeEnum.REQUIREMENTS_ANALYZER)
        )
        logger.debug("Added edge from TASK_BREAKDOWN to REQUIREMENTS_ANALYZER.")

        planner_work_flow.add_edge(
            str(PlannerNodeEnum.REQUIREMENTS_ANALYZER),
            str(PlannerNodeEnum.EXIT)
        )
        logger.debug("Added edge from REQUIREMENTS_ANALYZER to EXIT.")

        planner_work_flow.add_edge(
            str(PlannerNodeEnum.ISSUE_BREAKDOWN),
            str(PlannerNodeEnum.EXIT)
        )
        logger.debug("Added edge from ISSUE_BREAKDOWN to EXIT.")

        planner_work_flow.set_entry_point(str(PlannerNodeEnum.ENTRY))
        logger.debug("Set graph entry point to: %s", str(PlannerNodeEnum.ENTRY))
        planner_work_flow.set_finish_point(str(PlannerNodeEnum.EXIT))
        logger.debug("Set graph finish point to: %s", str(PlannerNodeEnum.EXIT))

        logger.info("Planner graph defined successfully with nodes: %s", list(nodes.keys()))
        return planner_work_flow
