from enum import Enum


class ReviewerMode(str, Enum):
    """Reviewer mode."""

    UNDER_REVIEW = "review"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class ReviewStage(str, Enum):
    """Reviewer stage."""

    STATIC_ANALYSIS = "static_code_analysis"
    FINISHED = "finished"

    def __str__(self):
        return self.value
