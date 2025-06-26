"""
Abstract interface for query engine operations.
"""

from abc import ABC, abstractmethod
from typing import List
from ..models.query_models import QueryRequest, QueryResponse


class QueryEngine(ABC):
    """Abstract interface for querying codebase information."""
    
    @abstractmethod
    def execute_query(self, request: QueryRequest) -> QueryResponse:
        """Execute a query against the codebase."""
        pass
    
    @abstractmethod
    def get_supported_query_types(self) -> List[str]:
        """Get list of supported query types."""
        pass
    
    @abstractmethod
    def validate_query(self, request: QueryRequest) -> bool:
        """Validate a query request."""
        pass