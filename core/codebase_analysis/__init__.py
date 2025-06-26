"""
Modular Codebase Analysis Component for GenPod

This module provides a pluggable codebase analysis system that can be easily
extended or replaced with different implementations (LocAgent, LSP, etc.).

Key Features:
- Context creation and management
- Query interface for codebase facts
- Bug impact analysis
- Dependency tracing
- Storage abstraction

Example Usage:
    from core.codebase_analysis import CodebaseAnalysisFactory
    
    analyzer = CodebaseAnalysisFactory.create(
        config_path="analysis_config.yaml",
        storage_base_path="/path/to/.genpod"
    )
    
    # Build context
    context = analyzer.build_context("/path/to/source/code")
    
    # Query codebase
    summary = analyzer.get_summary()
    
    # Analyze bug impact
    impact = analyzer.analyze_bug_impact(exception_trace)
"""

from .factories.analysis_factory import CodebaseAnalysisFactory
from .models.context_models import CodebaseContext, CodebaseStats
from .models.query_models import QueryRequest, QueryResponse
from .models.response_models import BugImpactResult, CodebaseFactResult

__version__ = "1.0.0"
__all__ = [
    "CodebaseAnalysisFactory",
    "CodebaseContext",
    "CodebaseStats", 
    "QueryRequest",
    "QueryResponse",
    "BugImpactResult",
    "CodebaseFactResult"
]