# reviewer_node_enum.py
from dataclasses import dataclass


@dataclass
class ReviewerNodeEnum:
    """Enumeration for Reviewer workflow nodes."""
    ENTRY = "entry"
    RUN_CHECKS = "run_checks"
    GENERATE_DOCUMENTATION = "generate_documentation"
    EXIT = "exit"
