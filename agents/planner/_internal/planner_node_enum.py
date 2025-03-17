from enum import Enum


class PlannerNodeEnum(str, Enum):
    """Enum for PlannerNode."""

    ENTRY = "entry"
    TASK_BREAKDOWN = "task_breakdown"
    REQUIREMENTS_ANALYZER = "requirements_analyzer"
    ISSUE_BREAKDOWN = "issue_breakdown"
    EXIT = "exit"

    def __str__(self):
        return self.value
