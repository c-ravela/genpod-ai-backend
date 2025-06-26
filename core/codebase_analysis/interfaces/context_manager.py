"""
Abstract interface for context management operations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..models.context_models import CodebaseContext


class ContextManager(ABC):
    """Abstract interface for managing codebase context."""
    
    @abstractmethod
    def build_context(self, source_path: str, **kwargs) -> CodebaseContext:
        """Build codebase context from source."""
        pass
    
    @abstractmethod
    def update_context(self, source_path: Optional[str] = None) -> CodebaseContext:
        """Update existing context."""
        pass
    
    @abstractmethod
    def save_context(self, context: CodebaseContext) -> None:
        """Save context to storage."""
        pass
    
    @abstractmethod
    def load_context(self) -> Optional[CodebaseContext]:
        """Load context from storage."""
        pass
    
    @abstractmethod
    def is_context_valid(self) -> bool:
        """Check if current context is valid."""
        pass