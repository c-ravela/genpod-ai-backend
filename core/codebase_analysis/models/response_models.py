"""
Data models for analysis responses and results.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class DependencyInfo:
    """Information about a dependency relationship."""
    
    source_entity: str
    target_entity: str
    dependency_type: str  # import, call, inheritance, etc.
    file_path: str
    line_number: Optional[int] = None
    context: Optional[str] = None
    strength: float = 1.0  # Dependency strength/importance
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImpactedCode:
    """Represents code that is impacted by a change or bug."""
    
    entity_id: Optional[str]
    entity_name: str
    entity_type: str
    file_path: str
    line_number: Optional[int] = None
    
    # Impact details
    impact_type: str  # direct, indirect, transitive
    impact_reason: str  # why this code is impacted
    impact_level: str  # high, medium, low
    
    # Context
    code_snippet: Optional[str] = None
    surrounding_context: Optional[str] = None
    
    # Risk assessment
    risk_score: float = 0.5  # 0.0 to 1.0
    change_complexity: str = "unknown"  # simple, moderate, complex
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BugImpactResult:
    """
    Result of bug impact analysis.
    
    Contains information about what code might be affected by a bug
    and what changes might be needed to fix it.
    """
    
    bug_description: str
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    
    # Primary impact locations
    primary_locations: List[ImpactedCode] = field(default_factory=list)
    
    # Secondary impact (dependent code)
    secondary_impacts: List[ImpactedCode] = field(default_factory=list)
    
    # Call chains that might be affected
    affected_call_chains: List[List[str]] = field(default_factory=list)
    
    # Dependencies that might need checking
    dependency_impacts: List[DependencyInfo] = field(default_factory=list)
    
    # Analysis metadata
    analysis_method: str = "static"  # static, dynamic, ai-assisted
    confidence_score: float = 0.5
    analysis_time: float = 0.0  # seconds
    
    # Recommendations
    suggested_fixes: List[str] = field(default_factory=list)
    testing_recommendations: List[str] = field(default_factory=list)
    risk_assessment: str = "medium"  # low, medium, high, critical
    
    # Additional context
    related_files: List[str] = field(default_factory=list)
    similar_patterns: List[str] = field(default_factory=list)
    
    def get_high_risk_impacts(self) -> List[ImpactedCode]:
        """Get impacts with high risk scores."""
        return [impact for impact in self.primary_locations + self.secondary_impacts 
                if impact.risk_score >= 0.7]
    
    def get_files_to_review(self) -> List[str]:
        """Get unique list of files that should be reviewed."""
        files = set()
        for impact in self.primary_locations + self.secondary_impacts:
            files.add(impact.file_path)
        files.update(self.related_files)
        return list(files)
    
    def to_summary(self) -> Dict[str, Any]:
        """Get a summary of the impact analysis."""
        return {
            "total_primary_impacts": len(self.primary_locations),
            "total_secondary_impacts": len(self.secondary_impacts),
            "high_risk_count": len(self.get_high_risk_impacts()),
            "files_to_review": len(self.get_files_to_review()),
            "confidence_score": self.confidence_score,
            "risk_assessment": self.risk_assessment,
            "analysis_time": self.analysis_time
        }


@dataclass
class CodebaseFactResult:
    """
    Result containing factual information about the codebase.
    
    Used for summary and statistical queries.
    """
    
    query: str
    response_type: str  # summary, statistics, facts
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Main response content
    summary_text: Optional[str] = None
    facts: Dict[str, Any] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    # Supporting data
    key_entities: List[str] = field(default_factory=list)
    key_files: List[str] = field(default_factory=list)
    key_relationships: List[DependencyInfo] = field(default_factory=list)
    
    # Metadata
    confidence_score: float = 1.0
    data_freshness: Optional[datetime] = None  # When underlying data was last updated
    
    # Visual data for charts/graphs
    charts_data: Dict[str, Any] = field(default_factory=dict)
    
    def add_fact(self, key: str, value: Any, description: Optional[str] = None) -> None:
        """Add a fact to the result."""
        self.facts[key] = {
            "value": value,
            "description": description,
            "timestamp": datetime.now()
        }
    
    def add_statistic(self, key: str, value: Any, unit: Optional[str] = None) -> None:
        """Add a statistic to the result."""
        self.statistics[key] = {
            "value": value,
            "unit": unit,
            "timestamp": datetime.now()
        }
    
    def to_json_response(self) -> Dict[str, Any]:
        """Convert to JSON response format."""
        return {
            "query": self.query,
            "response_type": self.response_type,
            "summary": self.summary_text,
            "facts": {k: v["value"] for k, v in self.facts.items()},
            "statistics": {k: v["value"] for k, v in self.statistics.items()},
            "key_entities": self.key_entities,
            "key_files": self.key_files,
            "confidence_score": self.confidence_score,
            "data_freshness": self.data_freshness.isoformat() if self.data_freshness else None,
            "charts_data": self.charts_data
        }
