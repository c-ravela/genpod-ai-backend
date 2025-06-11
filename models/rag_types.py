from enum import Enum


class RAGType(str, Enum):
    """
    Which RAG pipeline to spin up.
    """
    LANGCHAIN_VECTOR = "langchain"
    LLAMA_INDEX      = "llama_index"

    def __str__(self) -> str:
        return self.value
