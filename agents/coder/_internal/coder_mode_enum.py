from enum import Enum


class CoderMode(str, Enum):
    CODE_GENERATION = "code_generation"
    ISSUE_RESOLUTION = "resolving_issues"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class CodeGenerationStage(str, Enum):
    GENERATE_CODE = "generate_code"
    GENERATE_CODE_FROM_SKELETON = "generate_code_from_skeleton"
    SAVE_CODE = "save_code"
    ADD_LICENSE_HEADER = "add_license_header"
    DOWNLOAD_LICENSE_FILE = "download_license_file"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class ResolveIssueStage(str, Enum):
    RESOLVE_ISSUE = "resolve_issue"
    SAVE_CODE = "save_code"
    ADD_LICENSE_HEADER = "add_license_header"
    FINISHED = "finished"

    def __str__(self):
        return self.value
