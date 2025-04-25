from enum import Enum


class ReviewerMode(str, Enum):
    """Reviewer operational mode."""
    UNDER_REVIEW = "under_review"
    FINISHED = "finished"

    def __str__(self):
        return self.value

class ReviewStage(str, Enum):
    """Reviewer stage in the workflow."""
    INITIALIZATION = "initialization"
    RUN_CHECKS = "run_checks"
    FINISHED = "finished"

    def __str__(self):
        return self.value
