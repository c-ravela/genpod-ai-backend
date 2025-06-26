"""
Abstract interface for impact analysis operations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models.response_models import BugImpactResult


class ImpactAnalyzer(ABC):
    """Abstract interface for analyzing code impact and dependencies."""
    
    @abstractmethod
    def analyze_bug_impact(self, bug_details: str, **kwargs) -> BugImpactResult:
        """Analyze impact of a bug or error."""
        pass
    
    @abstractmethod
    def find_dependent_code(self, 
                           file_path: str, 
                           function_name: Optional[str] = None,
                           class_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find code that depends on specified component."""
        pass
    
    @abstractmethod
    def get_call_chain(self, target_function: str, max_depth: int = 5) -> List[List[str]]:
        """Get call chains leading to target function."""
        pass
    
    @abstractmethod
    def analyze_change_impact(self, 
                             changed_files: List[str],
                             change_type: str = "modification") -> Dict[str, Any]:
        """Analyze impact of code changes."""
        pass