from enum import Enum


class RAGMiddlewareMode(str, Enum):
    """
    Represents the overall modes of the RAG middleware.
    """
    PROCESSING_QUERY = "processing_query"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class RAGQueryStage(str, Enum):
    """
    Represents the stages of processing a query within the RAG middleware.
    """
    EVALUATE_QUERY = "evaluate_query"
    SELECT_AGENT = "select_agent"
    FORWARD_TO_RAG = "forward_to_rag"
    REFINE_RESPONSE = "refine_response"
    FINISHED = "finished"
