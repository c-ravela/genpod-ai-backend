from typing import Any, Dict

from pydantic import Field

from core.state.base_state import *


class RAGInputState(BaseInputState):
    """
    Represents the input state for a RAG agent.

    Attributes:
        query (str): The query that needs to be addressed by the RAG agent.
    """
    query: str = Field(
        description="The query that needs to be addressed by the RAG agent."
    )


class RAGOutputState(BaseOutputState):
    """
    Represents the output state for a RAG agent.

    Attributes:
        metadata (Dict[str, Any]): Metadata related to the generated answer,
            such as the document name or excerpts used to produce the response.
        response_type (str): Indicates how the response was generated (e.g.,
            'rag_answered', 'rag_cache', 'rejected').
        response (str): The response produced by the RAG agent.
    """
    metadata: Dict[str, Any] = Field(
        description="Metadata related to the answer (e.g., document name, content excerpt)."
    )
    response_type: str = Field(
        description=("Indicates how the response was generated (e.g., 'rag_answered', "
                     "'no_rag_to_answer', 'rag_cache', 'rejected').")
    )
    response: str = Field(
        description="The response produced by the RAG agent."
    )


class RAGState(BaseState):
    """
    Unified state model for RAG agents.

    This model encapsulates the essential information required for a RAG agent to process a query
    and generate a response. It standardizes the state so that middleware components and RAG agents
    can interact using a consistent data structure.

    Attributes:
        query (str): The query that needs to be addressed by the RAG agent.
        metadata (Dict[str, Any]): A dictionary holding metadata associated with the generated response,
            such as document names or content excerpts.
        response_type (str): A string indicating how the response was generated. Examples include:
            - 'rag_answered': The query was successfully answered by a RAG agent.
            - 'no_rag_to_answer': No suitable RAG agent was available to answer the query.
            - 'rag_cache': The response was retrieved from a cache.
            - 'rejected': The query was rejected due to errors or other conditions.
        response (str): The actual response produced by the RAG agent.
    """
    query: str = Field(
        default="",
        description="The query that needs to be addressed by the RAG agent."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata associated with the response (e.g., document name, content excerpt)."
    )
    response_type: str = Field(
        default="",
        description=("Indicates how the response was generated (e.g., 'rag_answered', 'no_rag_to_answer', "
                     "'rag_cache', 'rejected').")
    )
    response: str = Field(
        default="",
        description="The response produced by the RAG agent."
    )
