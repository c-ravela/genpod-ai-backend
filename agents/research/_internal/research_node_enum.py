from enum import Enum


class ResearchNodeEnum(str, Enum):
    """Enum for research node types."""

    ENTRY = "entry"
    SOURCE_DRIVEN_RESEARCH = "source_driven_research"
    OPEN_WEB_RESEARCH = "open_web_research"
    SEARCH_RESULTS_ASSESSMENT = "search_results_assessment"
    RESPONSE_GENERATION = "response_generation"
    EXIT = "exit"

    def __str__(self) -> str:
        return self.value
