from enum import Enum


class PlannerMode(str, Enum):
    """Represents the current state or mode of the planning process."""

    TASK_PLANNING = "task_planning"
    ISSUE_PLANNING = "issue_planning"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class TaskPlanningStage(str, Enum):
    TASK_BREAKDOWN = "task_breakdown"
    REQUIREMENTS_ANALYZER = "requirements_analyzer"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class IssuePlanningStage(str, Enum):
    ISSUE_BREAKDOWN = "issue_breakdown"
    FINISHED = "finished"

    def __str__(self):
        return self.value
