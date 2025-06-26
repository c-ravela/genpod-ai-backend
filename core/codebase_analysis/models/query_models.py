"""
Data models for query requests and responses.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class QueryType(Enum):
    """Types of queries supported by the system."""
    
    # Simple lookups
    FIND_FUNCTION = "find_function"
    FIND_CLASS = "find_class"
    FIND_FILE = "find_file"
    FIND_VARIABLE = "find_variable"
    
    # Complex analysis
    GET_DEPENDENCIES = "get_dependencies"
    GET_DEPENDENTS = "get_dependents"
    GET_CALL_CHAIN = "get_call_chain"
    GET_INHERITANCE_HIERARCHY = "get_inheritance_hierarchy"
    
    # Natural language
    NATURAL_LANGUAGE = "natural_language"
    
    # Statistics and summaries
    GET_STATS = "get_stats"
    GET_SUMMARY = "get_summary"
    GET_FILE_INFO = "get_file_info"
    
    # Search queries
    SEARCH_CODE = "search_code"
    SEARCH_COMMENTS = "search_comments"
    SEARCH_DOCUMENTATION = "search_documentation"
    
    # Impact analysis
    ANALYZE_IMPACT = "analyze_impact"
    FIND_SIMILAR_CODE = "find_similar_code"


@dataclass
class QueryRequest:
    """Request for querying the codebase."""
    
    query_type: QueryType
    query: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Response formatting options
    include_source_code: bool = True
    include_metadata: bool = True
    max_results: int = 50
    context_lines: int = 5
    
    # Filter options
    file_patterns: Optional[List[str]] = None  # Glob patterns for files to include
    exclude_patterns: Optional[List[str]] = None  # Patterns to exclude
    entity_types: Optional[List[str]] = None  # Types of entities to include
    
    def __post_init__(self):
        """Validate and normalize the request."""
        if isinstance(self.query_type, str):
            self.query_type = QueryType(self.query_type)
        
        # Normalize patterns
        if self.file_patterns and isinstance(self.file_patterns, str):
            self.file_patterns = [self.file_patterns]
        if self.exclude_patterns and isinstance(self.exclude_patterns, str):
            self.exclude_patterns = [self.exclude_patterns]
        if self.entity_types and isinstance(self.entity_types, str):
            self.entity_types = [self.entity_types]


@dataclass
class QueryMatch:
    """Represents a single match from a query."""
    
    entity_id: Optional[str]
    entity_name: str
    entity_type: str
    file_path: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    
    # Content
    matched_content: Optional[str] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    full_content: Optional[str] = None
    
    # Scoring and ranking
    confidence_score: float = 1.0
    relevance_score: float = 1.0
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResponse:
    """Response to a codebase query."""
    
    request: QueryRequest
    matches: List[QueryMatch] = field(default_factory=list)
    
    # Response metadata
    total_matches: int = 0
    execution_time: float = 0.0  # seconds
    success: bool = True
    error_message: Optional[str] = None
    
    # Additional information
    suggested_queries: List[str] = field(default_factory=list)
    related_entities: List[str] = field(default_factory=list)
    
    # Raw results for complex queries
    raw_data: Optional[Dict[str, Any]] = None
    
    # For natural language responses
    natural_language_response: Optional[str] = None
    
    def get_best_matches(self, limit: int = 10) -> List[QueryMatch]:
        """Get the best matches sorted by relevance."""
        sorted_matches = sorted(self.matches, 
                              key=lambda m: (m.relevance_score, m.confidence_score), 
                              reverse=True)
        return sorted_matches[:limit]
    
    def get_matches_by_file(self) -> Dict[str, List[QueryMatch]]:
        """Group matches by file path."""
        by_file = {}
        for match in self.matches:
            if match.file_path not in by_file:
                by_file[match.file_path] = []
            by_file[match.file_path].append(match)
        return by_file
    
    def get_matches_by_type(self) -> Dict[str, List[QueryMatch]]:
        """Group matches by entity type."""
        by_type = {}
        for match in self.matches:
            if match.entity_type not in by_type:
                by_type[match.entity_type] = []
            by_type[match.entity_type].append(match)
        return by_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        from dataclasses import asdict
        data = asdict(self)
        data['request']['query_type'] = self.request.query_type.value
        return data
    
    def to_json_response(self) -> Dict[str, Any]:
        """Convert to JSON-serializable format for API responses."""
        return {
            "query": self.request.query,
            "query_type": self.request.query_type.value,
            "success": self.success,
            "total_matches": self.total_matches,
            "execution_time": self.execution_time,
            "matches": [
                {
                    "entity_name": match.entity_name,
                    "entity_type": match.entity_type,
                    "file_path": match.file_path,
                    "line_number": match.line_number,
                    "matched_content": match.matched_content,
                    "confidence_score": match.confidence_score,
                    "relevance_score": match.relevance_score,
                    "metadata": match.metadata
                }
                for match in self.matches
            ],
            "natural_language_response": self.natural_language_response,
            "suggested_queries": self.suggested_queries,
            "error_message": self.error_message
        }
