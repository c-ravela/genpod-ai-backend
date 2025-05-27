from langgraph.graph import StateGraph

from agents.llama_index_vector_rag._internal.llama_index_vector_rag_nodes import \
    LlamaRAGNode
from agents.llama_index_vector_rag._internal.llama_index_vector_rag_state import (
    LlamaIndexVectorOutput, LlamaIndexVectorState)
from agents.llama_index_vector_rag._internal.llama_index_vector_rag_workflow import \
    LlamaIndexVectorRAGWorkFlow
from core.graph import BaseGraph
from utils.logger import logger


class LlamaIndexVectorRAGGraph(BaseGraph[LlamaIndexVectorRAGWorkFlow]):
    """
    Graph for the single-pass LlamaIndexVector RAG workflow.
    Defines transitions: ENTRY -> EXECUTE_QUERY -> EXIT
    """

    def __init__(
        self,
        workflow: LlamaIndexVectorRAGWorkFlow,
        recursion_limit: int,
        persistence_db_path: str
    ):
        super().__init__(workflow, recursion_limit, persistence_db_path)
        logger.info(
            "Initialized LlamaIndexVectorRAGGraph with recursion_limit=%d, persistence_db_path='%s'",
            recursion_limit, persistence_db_path
        )

    def define_graph(self) -> StateGraph:
        logger.info("Defining single-pass RAG workflow graph...")
        graph = StateGraph(
            LlamaIndexVectorState,
            input=LlamaIndexVectorState,
            output=LlamaIndexVectorOutput
        )

        # Add nodes
        graph.add_node(LlamaRAGNode.ENTRY, self.work_flow.entry_node)
        graph.add_node(LlamaRAGNode.EXECUTE_QUERY, self.work_flow.execute_query_node)
        graph.add_node(LlamaRAGNode.EXIT, self.work_flow.exit_node)

        # Conditional edges
        graph.add_conditional_edges(
            LlamaRAGNode.ENTRY,
            self.work_flow.router,
            {LlamaRAGNode.EXECUTE_QUERY: LlamaRAGNode.EXECUTE_QUERY}
        )
        graph.add_conditional_edges(
            LlamaRAGNode.EXECUTE_QUERY,
            self.work_flow.router,
            {
                LlamaRAGNode.EXECUTE_QUERY: LlamaRAGNode.EXECUTE_QUERY,
                LlamaRAGNode.EXIT: LlamaRAGNode.EXIT
            }
        )

        # Entry and exit
        graph.set_entry_point(LlamaRAGNode.ENTRY)
        graph.set_finish_point(LlamaRAGNode.EXIT)

        logger.info(
            "Graph entry set to '%s', finish set to '%s'",
            LlamaRAGNode.ENTRY, LlamaRAGNode.EXIT
        )
        logger.info("Single-pass RAG workflow graph defined.")

        return graph
