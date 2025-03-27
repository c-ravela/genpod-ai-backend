from enum import Enum


class PlannerMode(str, Enum):
    """
    Enumerates the primary modes of the planning process.

    Modes:
        TASK_PLANNING: The process is focused on analyzing deliverables and generating tasks.
        ISSUE_PLANNING: The process is focused on analyzing issues and planning corrective actions.
        FINISHED: The planning process has been completed.
    """
    TASK_PLANNING = "task_planning"
    ISSUE_PLANNING = "issue_planning"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class TaskPlanningStage(str, Enum):
    """
    Enumerates the stages within the task planning process.

    Stages:
        DELIVERABLE_BREAKDOWN: Stage where each deliverable is broken down into smaller work items.
        REQUIREMENTS_ANALYSIS: Stage where detailed requirements for each work item are analyzed.
        TASK_WORKPACKAGE_UPDATE: Stage where generated task work packages are updated based on human feedback.
        FINISHED: Task planning is complete.
    """
    DELIVERABLE_BREAKDOWN = "deliverable_breakdown"
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    TASK_WORKPACKAGE_UPDATE = "task_workpackage_update"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class IssuePlanningStage(str, Enum):
    """
    Enumerates the stages within the issue planning process.

    Stages:
        ISSUE_BREAKDOWN: Stage where an issue is analyzed and broken down for planning corrective actions.
        ISSUE_WORKPACKAGE_UPDATE: Stage where generated issue work packages are updated based on human feedback.
        FINISHED: Issue planning is complete.
    """
    ISSUE_BREAKDOWN = "issue_breakdown"
    ISSUE_WORKPACKAGE_UPDATE = "issue_workpackage_update"
    FINISHED = "finished"

    def __str__(self):
        return self.value
