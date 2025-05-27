from typing import Optional

from core.agent import BaseAgent
from llms.llm import LLM
from agents.langchain_vector_rag import RAGAgent
from agents.llama_index_vector_rag import LlamaIndexVectorRAGAgent
from models.rag_types import RAGType


def create_rag(
    rag_type: RAGType,
    agent_id: str,
    agent_name: str,
    description: str,
    llm: LLM,
    recursion_limit: int,
    persistence_db_path: str,
    *,
    collection_name: Optional[str] = None,
    persist_directory: Optional[str] = None,
    config_path: Optional[str] = None
) -> BaseAgent:
    """
    Factory function to instantiate the appropriate RAG workflow.

    Args:
        rag_type: The desired RAG workflow type.
        agent_id: Unique identifier for the agent.
        agent_name: Human-readable name for the agent.
        llm: The language model instance used by the workflow.
        collection_name: Name of the Chroma collection (required for LANGCHAIN_VECTOR).
        persist_directory: Directory path to persist the vector store (required for LANGCHAIN_VECTOR).

    Returns:
        An instance of BaseAgent implementing the selected workflow.

    Raises:
        ValueError: If the rag_type is unrecognized, or required parameters are missing.
    """
    if rag_type == RAGType.LANGCHAIN_VECTOR:
        if not collection_name or not persist_directory:
            raise ValueError(
                "`collection_name` and `persist_directory` must be provided for LANGCHAIN_VECTOR workflow"
            )
        return RAGAgent(
            id=agent_id,
            name=agent_name,
            description=description,
            llm=llm,
            collection_name=collection_name,
            persist_directory=persist_directory,
            recursion_limit=recursion_limit,
            persistence_db_path=persistence_db_path
        )

    if rag_type == RAGType.LLAMA_INDEX:
        return LlamaIndexVectorRAGAgent(
            id=agent_id,
            name=agent_name,
            description=description,
            llm=llm,
            recursion_limit=recursion_limit,
            persistence_db_path=persistence_db_path,
            config_path=config_path
        )

    raise ValueError(f"Unknown RAGType: {rag_type}")
