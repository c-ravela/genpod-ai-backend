from enum import Enum


class ReviewerNodeEnum(str, Enum):
    """Reviewer Node Enum"""

    ENTRY = "entry"
    STATIC_CODE_ANALYSIS = "static_code_analysis"
    EXIT = "exit"

    def __str__(self):
        return self.value
