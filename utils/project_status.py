from tabulate import tabulate
from utils.logs.logging_utils import logger

class ProjectStatus:
    def __init__(self, data):
        """Initialize the ProjectStatus with the provided data."""
        self.data = data
        logger.info("ProjectStatus initialized.")

    def _truncate_text(self, text, max_length=100):
        """Truncate text to a specified length and append '...' if it's too long."""
        truncated = text if len(text) <= max_length else text[:max_length] + "..."
        logger.debug(f"Truncated text: {truncated}")
        return truncated

    def _count_completed_items(self, items):
        """Count completed items based on the 'task_status', 'issue_status', or 'status' field."""
        count = 0
        for item in items:
            status = getattr(item, "task_status", None) or getattr(item, "issue_status", None) or getattr(item, "status", None)
            if str(status) == "DONE":
                count += 1
        logger.debug(f"Counted {count} completed items out of {len(items)} total items.")
        return count

    def _calculate_completion_percentage(self):
        """Calculate the completion percentage based on all tasks, planned tasks, issues, and planned issues."""
        try:
            tasks = getattr(self.data.get("tasks"), "items", [])
            planned_tasks = getattr(self.data.get("planned_tasks"), "items", [])
            issues = getattr(self.data.get("issues"), "items", [])
            planned_issues = getattr(self.data.get("planned_issues"), "items", [])

            completed_items = (
                self._count_completed_items(tasks) +
                self._count_completed_items(planned_tasks) +
                self._count_completed_items(issues) +
                self._count_completed_items(planned_issues)
            )

            total_items = len(tasks) + len(planned_tasks) + len(issues) + len(planned_issues)
            if total_items == 0:
                logger.debug("No items found to calculate completion percentage.")
                return "0.00%"

            completion_percentage = (completed_items / total_items) * 100
            logger.debug(f"Completion percentage calculated: {completion_percentage:.2f}%")
            return f"{completion_percentage:.2f}%"
        except Exception as e:
            logger.error(f"Error calculating completion percentage: {e}")
            raise

    def display_project_status(self) -> str:
        """Display core project information in a table format on CLI."""
        try:
            completion_percentage = self._calculate_completion_percentage()

            project_info = [
                ["Project Name", self.data.get("project_name", "N/A")],
                ["Project Status", self.data.get("project_status", "N/A")],
                ["Completion Percentage", completion_percentage],
                ["Agents Status", self.data.get("agents_status", "N/A")],
                ["Microservice Name", self.data.get("microservice_name", "N/A")],
                ["Original Input", self._truncate_text(self.data.get("original_user_input", "N/A"), max_length=38)],
                ["Project Path", self.data.get("project_path", "N/A")]
            ]

            current_task = self.data.get("current_task", {})
            tasks = getattr(self.data.get("tasks"), "items", [])
            current_task_index = next((i for i, task in enumerate(tasks) if getattr(task, "task_id", None) == getattr(current_task, "task_id", None)), -1)
            task_info = [
                ["Current Task Description", self._truncate_text(getattr(current_task, "description", "N/A"), max_length=38)],
                ["Current Task Index", current_task_index + 1 if current_task_index != -1 else 0],
                ["Total Number of Tasks", len(tasks)]
            ]

            current_planned_task = self.data.get("current_planned_task", {})
            planned_tasks = getattr(self.data.get("planned_tasks"), "items", [])
            current_planned_task_index = next((i + 1 for i, task in enumerate(planned_tasks) if getattr(task, "task_id", None) == getattr(current_planned_task, "task_id", None)), 0)
            planned_task_info = [
                ["Current Planned Task Index", current_planned_task_index],
                ["Total Number of Planned Tasks", len(planned_tasks)]
            ]

            current_issue = self.data.get("current_issue", {})
            issues = getattr(self.data.get("issues"), "items", [])
            current_issue_index = next((i + 1 for i, issue in enumerate(issues) if getattr(issue, "issue_id", None) == getattr(current_issue, "issue_id", None)), 0)
            issue_info = [
                ["Current Issue Index", current_issue_index],
                ["Total Number of Issues", len(issues)]
            ]

            logger.info("Preparing project status overview.")

            # Project Status Overview
            overview = "\n--- Project Status Overview ---\n"
            overview += tabulate(project_info, headers=["Attribute", "Details"], tablefmt="fancy_grid")

            logger.info("Preparing current task information.")

            # Current Task
            overview += "\n\n--- Current Task ---\n"
            overview += tabulate(task_info, headers=["Attribute", "Details"], tablefmt="fancy_grid")

            logger.info("Preparing current planned task information.")

            # Current Planned Task
            overview += "\n\n--- Current Planned Task ---\n"
            overview += tabulate(planned_task_info, headers=["Attribute", "Details"], tablefmt="fancy_grid")

            logger.info("Preparing current issue information.")

            # Current Issue
            overview += "\n\n--- Current Issue ---\n"
            overview += tabulate(issue_info, headers=["Attribute", "Details"], tablefmt="fancy_grid")

            logger.info("Returning the formatted project status overview.")
            return overview
        except Exception as e:
            logger.error(f"Error displaying project status: {e}")
            raise
