from enum import Enum


class ArchitectNodeEnum(str, Enum):
    ENTRY = "entry"
    GENERATE_REQUIREMENTS = "generate_requirements"
    EXTRACT_TASKS = "extract_tasks"
    SAVE_REQUIREMENTS = "save_requirements"
    GATHER_PROJECT_DETAILS = "gather_project_details"
    ADDITIONAL_INFO = "additional_info"
    EXIT = "exit"

    def __str__(self):
        return self.value
