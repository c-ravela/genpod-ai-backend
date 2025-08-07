from pydantic import Field
from core.state import RAGQueryInput, RAGQueryOutput, RAGQueryState


class LlamaIndexVectorInput(RAGQueryInput):
    """
    Input state for the RAG Agent.

    Inherits all fields from RAGQueryInput. No additional fields are defined.
    """
    pass


class LlamaIndexVectorOutput(RAGQueryOutput):
    """
    Output state for the RAG Agent.

    Inherits all fields from RAGQueryOutput with additional RAG-specific fields.
    """
    # Additional fields that the RAG server expects
    query: str = Field(
        default="",
        description="The original query that was processed."
    )
    sources: list = Field(
        default_factory=list,
        description="List of retrieved sources used to generate the response."
    )
    confidence_score: float = Field(
        default=0.0,
        description="Confidence score for the RAG response."
    )


class LlamaIndexVectorState(RAGQueryState):
    """
    Internal state for the RAG Agent.
    """
    pass
