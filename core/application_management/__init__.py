"""
Core Application Management Module

This module provides utilities for managing GenPod applications including:
- Application detection (GenPod projects and Git repositories)
- Basic .genpod folder management
- Session tracking integration
- Simple codebase analysis initialization

Simplified version focused on code editor requirements.
For codebase queries and operations, use core.codebase_analysis directly.
"""

from .detector import ApplicationDetector
from .manager import ApplicationManager
from .integration import get_codebase_analyzer, ensure_codebase_context

__version__ = "1.0.0"
__all__ = [
    "ApplicationDetector",
    "ApplicationManager", 
    "get_codebase_analyzer",
    "ensure_codebase_context"
]