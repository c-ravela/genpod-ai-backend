from typing import Dict

from pydantic import BaseModel, Field


class RagAgentDetail(BaseModel):
    """
    Model representing details about an agent's selection,
    including the reason for selection and a confidence score.
    """
    reason: str = Field(
        description="A brief explanation of why this agent is a suitable choice."
    )
    confidence: float = Field(
        description="A confidence score (e.g., 0.0 to 1.0) indicating the suitability of this agent."
    )


class RagSelectionResponse(BaseModel):
    """
    Model representing the response from the RAG agent selection process.
    """
    rag_agent_id: str = Field(
        description="The ID of the chosen RAG agent that can answer the given query."
    )
    details: Dict[str, RagAgentDetail] = Field(
        default_factory=dict,
        description="A mapping from agent name to its selection details, including the confidence score and reason."
    )
