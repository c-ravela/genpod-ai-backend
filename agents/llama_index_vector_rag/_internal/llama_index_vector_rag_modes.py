from dataclasses import dataclass


@dataclass(frozen=True)
class LlamaRAGMode:
    """
    High-level modes for the one-shot RAG workflow.
    """
    EXECUTE_QUERY: str = "execute_query"
    COMPLETED:     str = "completed"


@dataclass(frozen=True)
class LlamaRAGStage:
    """
    Detailed stages in the one-shot RAG workflow.
    """
    EXECUTE_QUERY: str = "execute_query"
    COMPLETED:     str = "completed"
