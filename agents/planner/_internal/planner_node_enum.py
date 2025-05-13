from enum import Enum


class PlannerNodeEnum(str, Enum):
    """
    Enumerates the nodes (steps) in the planning workflow.

    Nodes:
        entry: The entry node of the planning process.
        TASK_DELIVERABLE_BREAKDOWN: Node for breaking down deliverables into task work items.
        REQUIREMENTS_ANALYSIS: Node for analyzing detailed requirements for each task work item.
        TASK_WORKPACKAGE_UPDATE: Node for updating generated task work packages based on human feedback.
        ISSUE_BREAKDOWN: Node for analyzing and breaking down issues for planning corrective actions.
        ISSUE_WORKPACKAGE_UPDATE: Node for updating generated issue work packages based on human feedback.
        finished: The exit node indicating that the planning process has concluded.
    """
    ENTRY = "entry"
    TASK_DELIVERABLE_BREAKDOWN = "task_deliverable_breakdown"
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    TASK_WORKPACKAGE_UPDATE = "task_workpackage_update"
    ISSUE_BREAKDOWN = "issue_breakdown"
    ISSUE_WORKPACKAGE_UPDATE = "issue_workpackage_update"
    EXIT = "exit"

    def __str__(self):
        return self.value
