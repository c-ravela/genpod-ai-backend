"""
Abstract interfaces for codebase analysis components.

These interfaces define the contract that all implementations must follow,
enabling easy replacement of underlying tools (LocAgent, LSP, etc.).
"""

from .analyzer import CodebaseAnalyzer
from .context_manager import ContextManager
from .query_engine import QueryEngine
from .impact_analyzer import ImpactAnalyzer
from .storage import StorageInterface

__all__ = [
    "CodebaseAnalyzer",
    "ContextManager", 
    "QueryEngine",
    "ImpactAnalyzer",
    "StorageInterface"
]