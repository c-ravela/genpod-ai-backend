from typing import Dict

from pydantic import Field

from core.state import RAGQueryInput, RAGQueryOutput, RAGQueryState
from models import EvaluationDetail, WebSearchResults


class ResearchInput(RAGQueryInput):
    """
    Model representing the input for a research query in the RAG system.

    Inherits from RAGQueryInput and serves as the base for any research-specific input attributes.
    Since this is a Pydantic model, the default initialization behavior is inherited.
    """

    pass


class ResearchOutput(RAGQueryOutput):
    """
    Extended research output that includes detailed evaluation metrics for both the generated response
    and the source selection process. This model enriches the base RAGQueryOutput with additional
    evaluation details such as confidence scores and reasoning.

    Additional fields for detailed evaluation can be uncommented and utilized if required:
        - response_details: Detailed evaluation of the generated response.
        - source_evaluation_details: A mapping of source identifiers to their evaluation details.
    """
    pass
    # response_details: EvaluationDetail = Field(
    #     ...,
    #     description="Evaluation details of the generated response, including confidence scores and reasoning."
    # )
    # source_evaluation_details: Dict[str, EvaluationDetail] = Field(
    #     default_factory=dict,
    #     description="A mapping of source identifiers to their evaluation details (e.g., confidence scores and reasoning)."
    # )


class ResearchState(RAGQueryState):
    """
    Represents the state for a research query in the RAG system, including evaluation details,
    web search results, and a count of refinement attempts.

    Attributes:
        response_details: Evaluation details of the generated response.
        source_evaluation_details: A mapping of source identifiers to their evaluation details.
        search_results: Holds the results obtained from a web search.
        refinement_attempts: The number of times the response was refined.
    """
    response_details: EvaluationDetail = Field(
        default_factory=EvaluationDetail,
        description="Evaluation details of the generated response, including confidence scores and reasoning."
    )
    source_evaluation_details: Dict[str, EvaluationDetail] = Field(
        default_factory=dict,
        description="A mapping of source identifiers to their evaluation details (e.g., confidence scores and reasoning)."
    )

    # Internal
    search_results: WebSearchResults = Field(
        default_factory=WebSearchResults,
        description="Holds the results from web search."
    )

    refinement_attempts: int = Field(
        default=0,
        description="Check the number of refinement attempts."
    )
