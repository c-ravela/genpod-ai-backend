from typing import Dict, List

from pydantic import BaseModel, Field


class EvaluationDetail(BaseModel):
    """
    Represents evaluation details including the rationale and a confidence score.
    """
    reason: str = Field(
        default="",
        description="A brief explanation of the evaluation decision."
    )
    confidence: float = Field(
        default=0.0,
        description="A confidence score between 0.0 and 1.0, where 1.0 indicates maximum confidence.",
        ge=0.0,
        le=1.0
    )


class SourceSelectionResponse(BaseModel):
    """
    Model representing the response from the source selection process.
    """
    source_names: List[str] = Field(
        description="A list of source names or identifiers that have been selected as relevant for the given query."
    )
    details: Dict[str, EvaluationDetail] = Field(
        default_factory=dict,
        description="A mapping from each selected source name to its corresponding selection details, including the reason and confidence score."
    )


class RelevanceEvaluationResponse(BaseModel):
    """
    Represents the evaluation of the relevance of search results in relation to the original query.
    This evaluation determines whether the results adequately address the query and, if not, provides a refined query for further research.
    """
    is_relevant: bool = Field(
        description="Indicates whether the generated search results adequately address the original query."
    )
    refined_query: str = Field(
        default="",
        description="A revised search query recommended when the current results are unsatisfactory."
    )
    details: EvaluationDetail = Field(
        default_factory=lambda: EvaluationDetail(reason="", confidence=0.0),
        description="Detailed evaluation metrics, including reasoning and a confidence score, associated with the response."
    )


class GeneratedResponse(BaseModel):
    """
    Represents the final generated response derived from processed web search results.
    """
    content: str = Field(
        description="The final output text generated to answer the query based on the web search results."
    )
