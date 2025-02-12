from enum import Enum


class CoderNodeEnum(str, Enum):
    """
    An enumeration of node names used in the coder workflow.
    Each member represents a specific step or task in the process.
    """
    ENTRY = "entry"
    CODE_GENERATION = "code_generation"
    CODE_GENERATION_FROM_SKELETON = "code_generation"
    RESOLVE_ISSUE = "resolve_issue"
    WRITE_GENERATED_CODE = "write_generated_code"
    ADD_LICENSE = "add_license_text"
    DOWNLOAD_LICENSE = "download_license"
    EXIT = "exit"

    def __str__(self):
        return self.value
