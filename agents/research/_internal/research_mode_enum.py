from enum import Enum


class ResearchMode(str, Enum):
    """Defines the mode of research."""

    RESEARCH = "research"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class ResearchStage(str, Enum):
    """Represents different stages of research."""

    SOURCE_BASED_RESEARCH = "source_based_research" 
    OPEN_WEB_RESEARCH = "open_web_research" 
    RESULTS_ASSESSMENT = "results_assessment"
    RESPONSE_GENERATION = "response_generation"
    FINISHED = "finished"

    def __str__(self):
        return self.value
