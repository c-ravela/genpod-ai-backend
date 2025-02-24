from typing import Dict, Iterator

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


class AdditionalInfoRequest(BaseModel):
    """
    Model representing a request for additional information.

    This model is used when the system determines that more details are required 
    to accurately complete a task. It contains a single key "question", whose value 
    is the prompt asking for further information.
    """
    question: str = Field(..., description="The question prompting for additional information.")


class ErrorRegistry(BaseModel):
    registry: Dict[str, int] = Field(default_factory=dict)

    def __getitem__(self, key: str) -> int:
        # Return the error count for the key, or 0 if not found.
        return self.registry.get(key, 0)

    def __setitem__(self, key: str, value: int) -> None:
        self.registry[key] = value

    def get(self, key: str, default: int = 0) -> int:
        return self.registry.get(key, default)

    def __delitem__(self, key: str) -> None:
        if key in self.registry:
            del self.registry[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.registry)

    def items(self):
        return self.registry.items()

    def keys(self):
        return self.registry.keys()

    def __contains__(self, key: str) -> bool:
        return key in self.registry

    def __repr__(self) -> str:
        return f"ErrorRegistry({self.registry})"
