from langgraph.graph import StateGraph

from agents.rag_middleware._internal.rag_middleware_node_enum import \
    RAGMiddlewareNode
from agents.rag_middleware._internal.rag_middleware_state import *
from agents.rag_middleware._internal.rag_middleware_work_flow import *
from core.graph import BaseGraph
from utils.logs.logging_utils import logger


class RAGMiddlewareGraph(BaseGraph[RAGMiddlewareWorkFlow]):

    def __init__(
        self,
        work_flow: RAGMiddlewareWorkFlow,
        recursion_limit: int,
        persistence_db_path: str
    ):
        super().__init__(work_flow, recursion_limit, persistence_db_path)
    
    def define_graph(self) -> StateGraph:

        rag_middleware_flow_graph = StateGraph(RAGMiddlewareState, input=RAGMiddlewareInput, output=RAGMiddlewareOutput)

        rag_middleware_flow_graph.add_node(
            str(RAGMiddlewareNode.ENTRY),
            self.work_flow.entry_node
        )
        
        rag_middleware_flow_graph.add_node(
            str(RAGMiddlewareNode.QUERY_EVALUATION),
            self.work_flow.query_evaluation_node
        )
        rag_middleware_flow_graph.add_node(
            str(RAGMiddlewareNode.AGENT_SELECTION),
            self.work_flow.agent_selection_node
        )

        rag_middleware_flow_graph.add_node(
            str(RAGMiddlewareNode.FORWARD_TO_RAG),
            self.work_flow.forward_to_rag_node
        )

        rag_middleware_flow_graph.add_node(
            str(RAGMiddlewareNode.RESPONSE_REFINEMENT),
            self.work_flow.response_refinement_node
        )

        rag_middleware_flow_graph.add_node(
            str(RAGMiddlewareNode.EXIT),
            self.work_flow.exit_node
        )

        rag_middleware_flow_graph.add_conditional_edges(
            str(RAGMiddlewareNode.ENTRY),
            self.work_flow.router, {
            str(RAGMiddlewareNode.QUERY_EVALUATION):str(RAGMiddlewareNode.QUERY_EVALUATION),
            str(RAGMiddlewareNode.EXIT):str(RAGMiddlewareNode.EXIT)
        })

        rag_middleware_flow_graph.add_conditional_edges(
            str(RAGMiddlewareNode.QUERY_EVALUATION),
            self.work_flow.router, {
            str(RAGMiddlewareNode.AGENT_SELECTION):str(RAGMiddlewareNode.AGENT_SELECTION),
            str(RAGMiddlewareNode.EXIT):str(RAGMiddlewareNode.EXIT)
        })

        rag_middleware_flow_graph.add_conditional_edges(
            str(RAGMiddlewareNode.AGENT_SELECTION),
            self.work_flow.router, {
            str(RAGMiddlewareNode.FORWARD_TO_RAG):str(RAGMiddlewareNode.FORWARD_TO_RAG),
            str(RAGMiddlewareNode.EXIT):str(RAGMiddlewareNode.EXIT)
        })

        rag_middleware_flow_graph.add_conditional_edges(
            str(RAGMiddlewareNode.FORWARD_TO_RAG),
            self.work_flow.router, {
            str(RAGMiddlewareNode.RESPONSE_REFINEMENT):str(RAGMiddlewareNode.RESPONSE_REFINEMENT),
        })

        rag_middleware_flow_graph.add_conditional_edges(
            str(RAGMiddlewareNode.RESPONSE_REFINEMENT),
            self.work_flow.router, {
            str(RAGMiddlewareNode.EXIT):str(RAGMiddlewareNode.EXIT),
        })

        rag_middleware_flow_graph.set_entry_point(str(RAGMiddlewareNode.ENTRY))
        rag_middleware_flow_graph.set_finish_point(str(RAGMiddlewareNode.EXIT))
        return rag_middleware_flow_graph
