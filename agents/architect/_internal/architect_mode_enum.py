from enum import Enum


class ArchitectAgentMode(str, Enum):
    """
    Represents the overall mode of the Architect agent.
    """
    DOCUMENT_GENERATION = "document_generation"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class DocumentGenerationStage(str, Enum):
    """
    Represents different stages of the document generation process.
    """
    GENERATE_REQUIREMENTS = "generate_requirements"
    EXTRACT_TASKS = "extract_tasks"
    SAVE_REQUIREMENTS = "save_requirements"
    GATHER_PROJECT_DETAILS = "gather_project_details"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class InformationGatheringStage(str, Enum):
    """
    Represents different stages of the information gathering process.
    """
    IN_PROGRESS = "in_progress"
    REQUEST_ADDITIONAL_INFO = "request_additional_info"
    RECEIVE_ADDITIONAL_INFO = "receive_additional_info"
    FINISHED = "finished"

    def __str__(self):
        return self.value
