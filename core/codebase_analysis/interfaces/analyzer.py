"""
Abstract base class for codebase analyzers.

Defines the common interface and path management that all implementations share.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List

from utils.logger import logger
from ..models.context_models import CodebaseContext
from ..models.query_models import QueryRequest, QueryResponse
from ..models.response_models import BugImpactResult, CodebaseFactResult


class CodebaseAnalyzer(ABC):
    """
    Abstract base class for all codebase analysis implementations.
    
    Manages common concerns like storage paths, configuration, and logging.
    Concrete implementations (LocAgent, LSP, etc.) inherit from this class.
    """
    
    def __init__(self, storage_base_path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the analyzer with storage path and configuration.
        
        Args:
            storage_base_path: Path to .genpod folder where analysis data is stored
            config: Optional configuration dictionary
        """
        self.storage_base_path = Path(storage_base_path)
        self.config = config or {}
        self.logger = logger
        
        # Standard directory structure for ALL implementations
        self.code_analysis_dir = self.storage_base_path / "code_analysis"
        self.context_dir = self.code_analysis_dir / "context"
        self.vectors_dir = self.code_analysis_dir / "vectors"
        self.indexes_dir = self.code_analysis_dir / "indexes"
        self.cache_dir = self.code_analysis_dir / "cache"
        
        # Ensure directories exist
        self._ensure_directories()
        
        # State tracking
        self._context_loaded = False
        self._current_source_path = None
    
    
    def _ensure_directories(self) -> None:
        """Create the standard directory structure if it doesn't exist."""
        try:
            directories = [
                self.code_analysis_dir,
                self.context_dir,
                self.vectors_dir, 
                self.indexes_dir,
                self.cache_dir
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                
            self.logger.debug(f"Ensured directory structure at {self.code_analysis_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to create directory structure: {e}")
            raise
    
    def get_storage_info(self) -> Dict[str, str]:
        """Get information about storage paths and usage."""
        return {
            "base_path": str(self.storage_base_path),
            "code_analysis_dir": str(self.code_analysis_dir),
            "context_dir": str(self.context_dir),
            "vectors_dir": str(self.vectors_dir),
            "indexes_dir": str(self.indexes_dir),
            "cache_dir": str(self.cache_dir),
            "context_loaded": self._context_loaded,
            "current_source_path": str(self._current_source_path) if self._current_source_path else None
        }
    
    def cleanup_storage(self, confirm: bool = False) -> bool:
        """
        Clean up all stored analysis data.
        
        Args:
            confirm: Must be True to actually perform cleanup
            
        Returns:
            True if cleanup was performed, False otherwise
        """
        if not confirm:
            self.logger.warning("Cleanup called without confirmation - no action taken")
            return False
        
        try:
            import shutil
            if self.code_analysis_dir.exists():
                shutil.rmtree(self.code_analysis_dir)
                self.logger.info(f"Cleaned up analysis data at {self.code_analysis_dir}")
                
            # Recreate directory structure
            self._ensure_directories()
            self._context_loaded = False
            self._current_source_path = None
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup storage: {e}")
            return False
    
    # Abstract methods that concrete implementations must provide
    
    @abstractmethod
    def build_context(self, source_path: str, force_rebuild: bool = False) -> CodebaseContext:
        """
        Build or update codebase context from source code.
        
        Args:
            source_path: Path to source code to analyze
            force_rebuild: Whether to force a complete rebuild even if context exists
            
        Returns:
            CodebaseContext object with analysis results
        """
        pass
    
    @abstractmethod
    def update_context(self, source_path: Optional[str] = None) -> CodebaseContext:
        """
        Update existing context with changes.
        
        Args:
            source_path: Path to source code (uses last analyzed path if None)
            
        Returns:
            Updated CodebaseContext object
        """
        pass
    
    @abstractmethod
    def query_codebase(self, request: QueryRequest) -> QueryResponse:
        """
        Query the codebase for specific information.
        
        Args:
            request: Query request with type and parameters
            
        Returns:
            Query response with results
        """
        pass
    
    @abstractmethod
    def get_summary(self) -> CodebaseFactResult:
        """
        Get a high-level summary of the current codebase.
        
        Returns:
            Summary information about the codebase
        """
        pass
    
    @abstractmethod
    def analyze_bug_impact(self, 
                          bug_details: str,
                          context_lines: int = 5,
                          max_depth: int = 3) -> BugImpactResult:
        """
        Analyze the impact of a bug based on exception or error details.
        
        Args:
            bug_details: Exception message, stack trace, or bug description
            context_lines: Number of context lines to include around matches
            max_depth: Maximum depth for dependency impact analysis
            
        Returns:
            Bug impact analysis results
        """
        pass
    
    @abstractmethod
    def find_dependent_code(self, 
                           file_path: str, 
                           function_name: Optional[str] = None,
                           class_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find code that depends on the specified component.
        
        Args:
            file_path: Path to the file containing the component
            function_name: Optional specific function name
            class_name: Optional specific class name
            
        Returns:
            List of dependent code locations with metadata
        """
        pass
    
    @abstractmethod
    def get_call_chain(self, 
                      target_function: str,
                      max_depth: int = 5) -> List[List[str]]:
        """
        Get call chains leading to the target function.
        
        Args:
            target_function: Function to trace calls to
            max_depth: Maximum depth of call chain analysis
            
        Returns:
            List of call chains (each chain is a list of function names)
        """
        pass
    
    # Context management utilities
    
    def is_context_available(self) -> bool:
        """Check if context has been built and is available."""
        return self._context_loaded and (self.context_dir / "metadata.json").exists()
    
    def get_context_metadata(self) -> Optional[Dict[str, Any]]:
        """Get metadata about the current context."""
        if not self.is_context_available():
            return None
            
        try:
            import json
            metadata_file = self.context_dir / "metadata.json"
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read context metadata: {e}")
            return None
    
    def _save_context_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save context metadata to storage."""
        try:
            import json
            metadata_file = self.context_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save context metadata: {e}")
            raise