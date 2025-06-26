"""
Codebase Analysis Integration Module

Simple utility to initialize codebase analysis for applications.
Code editor should use core.codebase_analysis directly for all queries and operations.
"""

from pathlib import Path
from typing import Optional

from core.codebase_analysis import CodebaseAnalysisFactory
from utils.logger import logger


def get_codebase_analyzer(application_path: str):
    """
    Get a codebase analyzer instance for an application.
    
    Args:
        application_path (str): Path to the application
        
    Returns:
        Codebase analyzer instance or None if failed
        
    Example:
        analyzer = get_codebase_analyzer("/path/to/app")
        if analyzer:
            # Use analyzer directly - no wrapper methods needed
            summary = analyzer.get_summary()
            context = analyzer.build_context("/path/to/app")
            response = analyzer.query_codebase(request)
    """
    try:
        application_path = Path(application_path).resolve()
        genpod_path = application_path / ".genpod"
        
        analyzer = CodebaseAnalysisFactory.create(
            storage_base_path=str(genpod_path)
        )
        
        logger.info(f"Created codebase analyzer for: {application_path}")
        return analyzer
        
    except Exception as e:
        logger.error(f"Failed to create codebase analyzer: {e}")
        return None


def ensure_codebase_context(application_path: str, force_rebuild: bool = False) -> bool:
    """
    Ensure codebase context is built and ready.
    
    Args:
        application_path (str): Path to the application
        force_rebuild (bool): Force rebuild of context
        
    Returns:
        bool: True if context is ready
    """
    try:
        analyzer = get_codebase_analyzer(application_path)
        if not analyzer:
            return False
        
        # Check if context exists
        if not force_rebuild and analyzer.is_context_available():
            logger.info("Codebase context already available")
            return True
        
        # Build context
        logger.info("Building codebase context...")
        context = analyzer.build_context(str(application_path), force_rebuild=force_rebuild)
        
        if context:
            logger.info("Successfully built codebase context")
            return True
        else:
            logger.error("Failed to build codebase context")
            return False
            
    except Exception as e:
        logger.error(f"Failed to ensure codebase context: {e}")
        return False