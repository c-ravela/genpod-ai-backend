from enum import Enum


class RAGMiddlewareNode(str, Enum):
    """
    Enumeration of nodes in the RAG middleware process with clear, descriptive names.
    """
    ENTRY = "entry"
    QUERY_EVALUATION = "query_evaluation_node"
    AGENT_SELECTION = "agent_selection_node"
    FORWARD_TO_RAG = "forward_to_rag_node"
    RESPONSE_REFINEMENT = "response_refinement_node"
    EXIT = "exit"

    def __str__(self):
        return self.value
