"""
Utility modules for codebase analysis.
"""

from .git_hooks import GitHooksManager
from .error_handling import with_error_handling, AnalysisError

__all__ = ["GitHooksManager", "with_error_handling", "AnalysisError"]