from langgraph.graph import StateGraph

from agents.reviewer._internal.reviewer_node_enum import ReviewerNodeEnum
from agents.reviewer._internal.reviewer_state import (ReviewerInput,
                                                      ReviewerOutput,
                                                      ReviewerState)
from agents.reviewer._internal.reviewer_work_flow import ReviewerWorkFlow
from core.graph import BaseGraph
from utils.logs.logging_utils import logger


class ReviewerGraph(BaseGraph[ReviewerWorkFlow]):

    def __init__(
        self,
        work_flow: ReviewerWorkFlow,
        recursion_limit: int,
        persistence_db_path: str
    ):
        logger.info("Initializing ReviewerGraph with recursion_limit=%s and persistence_db_path=%s",
                    recursion_limit, persistence_db_path)
        super().__init__(work_flow, recursion_limit, persistence_db_path)

    def define_graph(self) -> StateGraph:
        reviewer_work_flow = StateGraph(ReviewerState, input=ReviewerInput, output=ReviewerOutput)

        reviewer_work_flow.add_node(str(ReviewerNodeEnum.ENTRY), self.work_flow.entry_node)
        reviewer_work_flow.add_node(str(ReviewerNodeEnum.STATIC_CODE_ANALYSIS), self.work_flow.static_code_analysis_node)
        reviewer_work_flow.add_node(str(ReviewerNodeEnum.EXIT), self.work_flow.exit_node)
        
        reviewer_work_flow.add_edge(
            str(ReviewerNodeEnum.ENTRY),
            str(ReviewerNodeEnum.STATIC_CODE_ANALYSIS)
        )
        
        reviewer_work_flow.add_conditional_edges(
            str(ReviewerNodeEnum.STATIC_CODE_ANALYSIS),
            self.work_flow.router,
            {
                str(ReviewerNodeEnum.EXIT): str(ReviewerNodeEnum.EXIT)
            }
        )

        reviewer_work_flow.set_entry_point(str(ReviewerNodeEnum.ENTRY))
        reviewer_work_flow.set_finish_point(str(ReviewerNodeEnum.EXIT))

        return reviewer_work_flow
