# reviewer_graph.py
from langgraph.graph import StateGraph

from agents.reviewer._internal.reviewer_node_enum import ReviewerNodeEnum
from agents.reviewer._internal.reviewer_state import (ReviewerInput,
                                                      ReviewerOutput,
                                                      ReviewerState)
from agents.reviewer._internal.reviewer_work_flow import ReviewerWorkFlow
from core.graph import BaseGraph
from utils.logger import logger


class ReviewerGraph(BaseGraph[ReviewerWorkFlow]):
    """
    Defines the graph for the Reviewer agent workflow.

    The graph consists of three nodes:
      - ENTRY: Initializes the review process.
      - RUN_CHECKS: Executes all configured checks sequentially.
      - EXIT: Finalizes the review process.
    """
    def __init__(self, work_flow: ReviewerWorkFlow, recursion_limit: int, persistence_db_path: str):
        logger.info("Initializing ReviewerGraph with recursion_limit=%s and persistence_db_path=%s",
                    recursion_limit, persistence_db_path)
        super().__init__(work_flow, recursion_limit, persistence_db_path)

    def define_graph(self) -> StateGraph:
        reviewer_work_flow = StateGraph(ReviewerState, input=ReviewerInput, output=ReviewerOutput)

        # Add nodes to the graph.
        reviewer_work_flow.add_node(str(ReviewerNodeEnum.ENTRY), self.work_flow.entry_node)
        reviewer_work_flow.add_node(str(ReviewerNodeEnum.RUN_CHECKS), self.work_flow.run_checks_node)
        reviewer_work_flow.add_node(str(ReviewerNodeEnum.EXIT), self.work_flow.exit_node)
        
        # Define edges between nodes.
        reviewer_work_flow.add_edge(str(ReviewerNodeEnum.ENTRY), str(ReviewerNodeEnum.RUN_CHECKS))
        reviewer_work_flow.add_edge(str(ReviewerNodeEnum.RUN_CHECKS), str(ReviewerNodeEnum.EXIT))
        
        reviewer_work_flow.set_entry_point(str(ReviewerNodeEnum.ENTRY))
        reviewer_work_flow.set_finish_point(str(ReviewerNodeEnum.EXIT))

        return reviewer_work_flow
