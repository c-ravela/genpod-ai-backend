"""
LocAgent implementation of codebase analysis interfaces.

This module provides concrete implementations of the analysis interfaces
using LocAgent as the underlying analysis engine.
"""

from .locagent_analyzer import LocAgentAnalyzer
from .locagent_storage import LocAgentStorageManager

__all__ = ["LocAgentAnalyzer", "LocAgentStorageManager"]