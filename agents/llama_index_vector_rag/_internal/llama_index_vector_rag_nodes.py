from dataclasses import dataclass


@dataclass(frozen=True)
class LlamaRAGNode:
    """
    Node identifiers for the simplified, single-pass RAG workflow.
    """
    ENTRY: str          = "entry"
    EXECUTE_QUERY: str  = "execute_query"
    EXIT: str           = "exit"
