"""
Factory for creating codebase analysis instances.

Provides a clean interface for instantiating analyzers while hiding
implementation details and enabling easy swapping of backends.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Type

from utils.logger import logger
from ..interfaces.analyzer import CodebaseAnalyzer
from ..config.config_manager import ConfigManager, Config


class CodebaseAnalysisFactory:
    """
    Factory class for creating codebase analyzer instances.
    
    This factory abstracts the creation of analyzer instances and enables
    easy switching between different implementations (LocAgent, LSP, etc.).
    """
    
    # Registry of available analyzer implementations
    _analyzers: Dict[str, Type[CodebaseAnalyzer]] = {}
    
    @classmethod
    def register_analyzer(cls, name: str, analyzer_class: Type[CodebaseAnalyzer]) -> None:
        """
        Register an analyzer implementation.
        
        Args:
            name: Name identifier for the analyzer (e.g., 'locagent', 'lsp')
            analyzer_class: The analyzer class to register
        """
        cls._analyzers[name] = analyzer_class
        logger.info(f"Registered analyzer: {name}")
    
    @classmethod
    def get_available_analyzers(cls) -> list[str]:
        """Get list of available analyzer implementations."""
        return list(cls._analyzers.keys())
    
    @classmethod
    def create(cls,
               storage_base_path: str,
               config_path: Optional[str] = None,
               analyzer_type: Optional[str] = None,
               config_dict: Optional[Dict[str, Any]] = None) -> CodebaseAnalyzer:
        """
        Create a codebase analyzer instance.
        
        Args:
            storage_base_path: Path to .genpod directory for storage
            config_path: Optional path to YAML configuration file
            analyzer_type: Specific analyzer type to use (overrides config)
            config_dict: Optional configuration dictionary (overrides file)
            
        Returns:
            Configured analyzer instance
            
        Raises:
            ValueError: If analyzer type is not available
            ImportError: If analyzer dependencies are not available
        """
        
        # Load configuration
        config_manager = ConfigManager()
        if config_dict:
            # Use provided config dictionary
            config = config_manager._dict_to_config(config_dict)
        else:
            # Load from file or defaults
            config = config_manager.load_config(config_path)
        
        # Determine analyzer type
        if analyzer_type:
            target_analyzer = analyzer_type
        else:
            target_analyzer = config.analyzer_type
        
        logger.info(f"Creating {target_analyzer} analyzer")
        
        # Ensure analyzer is registered
        if target_analyzer not in cls._analyzers:
            cls._register_builtin_analyzers()
        
        # Create analyzer instance
        if target_analyzer not in cls._analyzers:
            available = ", ".join(cls.get_available_analyzers())
            raise ValueError(f"Analyzer '{target_analyzer}' not available. Available: {available}")
        
        try:
            analyzer_class = cls._analyzers[target_analyzer]
            analyzer = analyzer_class(
                storage_base_path=storage_base_path,
                config=config.to_dict()
            )
            
            logger.info(f"Successfully created {target_analyzer} analyzer")
            return analyzer
            
        except ImportError as e:
            logger.error(f"Failed to create {target_analyzer} analyzer: {e}")
            raise ImportError(f"Dependencies for {target_analyzer} analyzer not available: {e}")
        except Exception as e:
            logger.error(f"Failed to create analyzer: {e}")
            raise
    
    @classmethod
    def create_with_auto_detection(cls,
                                  storage_base_path: str,
                                  config_path: Optional[str] = None) -> CodebaseAnalyzer:
        """
        Create analyzer with automatic detection of available implementations.
        
        Tries to create analyzers in order of preference, falling back to
        simpler implementations if dependencies are not available.
        
        Args:
            storage_base_path: Path to .genpod directory for storage
            config_path: Optional path to configuration file
            
        Returns:
            Best available analyzer instance
        """
        
        # Order of preference for analyzers
        preference_order = ['locagent', 'lsp', 'simple']
        
        cls._register_builtin_analyzers()
        
        for analyzer_type in preference_order:
            if analyzer_type in cls._analyzers:
                try:
                    logger.info(f"Attempting to create {analyzer_type} analyzer")
                    return cls.create(
                        storage_base_path=storage_base_path,
                        config_path=config_path,
                        analyzer_type=analyzer_type
                    )
                except ImportError as e:
                    logger.warning(f"Cannot use {analyzer_type} analyzer: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Failed to create {analyzer_type} analyzer: {e}")
                    continue
        
        raise RuntimeError("No analyzer implementations are available")
    
    @classmethod
    def _register_builtin_analyzers(cls) -> None:
        """Register built-in analyzer implementations."""
        if cls._analyzers:
            return  # Already registered
        
        
        # Try to register LocAgent analyzer
        try:
            from ..locagent_impl.locagent_analyzer import LocAgentAnalyzer
            cls.register_analyzer('locagent', LocAgentAnalyzer)
        except ImportError as e:
            logger.warning(f"LocAgent analyzer not available: {e}")
        
        # Register simple analyzer (always available)
        cls.register_analyzer('simple', SimpleCodebaseAnalyzer)
    
    @classmethod
    def create_from_config_file(cls, config_path: str, storage_base_path: str) -> CodebaseAnalyzer:
        """
        Create analyzer from configuration file.
        
        Args:
            config_path: Path to YAML configuration file
            storage_base_path: Path to .genpod directory for storage
            
        Returns:
            Configured analyzer instance
        """
        config_manager = ConfigManager()
        config = config_manager.load_config(config_path)
        
        return cls.create(
            storage_base_path=storage_base_path,
            config_dict=config.to_dict()
        )


# Simple fallback analyzer implementation
class SimpleCodebaseAnalyzer(CodebaseAnalyzer):
    """
    Simple fallback analyzer implementation.
    
    Provides basic functionality without external dependencies.
    Used as a fallback when other analyzers are not available.
    """
    
    def build_context(self, source_path: str, force_rebuild: bool = False):
        """Build basic context using file system analysis only."""
        from ..models.context_models import CodebaseContext, CodebaseStats
        from datetime import datetime
        
        source_path = Path(source_path)
        
        # Basic file counting
        py_files = list(source_path.rglob("*.py"))
        
        stats = CodebaseStats(
            total_files=len(py_files),
            total_lines=sum(self._count_file_lines(f) for f in py_files),
            total_functions=0,  # Would need parsing
            total_classes=0,    # Would need parsing
            total_variables=0,  # Would need parsing
            languages={"Python": len(py_files)},
            directories=list(set(str(f.parent) for f in py_files)),
            test_files=len([f for f in py_files if 'test' in f.name.lower()]),
            last_analysis=datetime.now()
        )
        
        context = CodebaseContext(
            source_path=str(source_path),
            storage_path=str(self.storage_base_path),
            stats=stats,
            analyzer_type="simple",
            analyzer_version="1.0.0"
        )
        
        self._context_loaded = True
        self._current_source_path = source_path
        
        return context
    
    def update_context(self, source_path: Optional[str] = None):
        """Update context (rebuild for simple analyzer)."""
        if source_path is None:
            source_path = self._current_source_path
        if source_path is None:
            raise ValueError("No source path available")
        return self.build_context(str(source_path), force_rebuild=True)
    
    def query_codebase(self, request):
        """Basic query implementation."""
        from ..models.query_models import QueryResponse
        
        return QueryResponse(
            request=request,
            success=False,
            error_message="Simple analyzer does not support advanced queries"
        )
    
    def get_summary(self):
        """Get basic summary."""
        from ..models.response_models import CodebaseFactResult
        
        if not self._context_loaded:
            raise ValueError("No context loaded")
        
        result = CodebaseFactResult(
            query="summary",
            response_type="summary",
            summary_text="Basic codebase analysis completed using simple analyzer."
        )
        
        return result
    
    def analyze_bug_impact(self, bug_details: str, context_lines: int = 5, max_depth: int = 3):
        """Basic bug impact analysis."""
        from ..models.response_models import BugImpactResult
        
        return BugImpactResult(
            bug_description=bug_details,
            analysis_method="simple",
            confidence_score=0.3,
            suggested_fixes=["Review the mentioned code locations manually"],
            risk_assessment="unknown"
        )
    
    def find_dependent_code(self, file_path: str, function_name: Optional[str] = None, class_name: Optional[str] = None):
        """Basic dependent code finder."""
        return []
    
    def get_call_chain(self, target_function: str, max_depth: int = 5):
        """Basic call chain analysis."""
        return []
    
    def _count_file_lines(self, file_path: Path) -> int:
        """Count lines in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return len(f.readlines())
        except Exception:
            return 0