"""
Error handling utilities for codebase analysis.

Provides decorators and exception classes for robust error handling.
"""

import functools
import traceback
from typing import Callable, Any, Optional, Dict

from utils.logger import logger as project_logger


class AnalysisError(Exception):
    """Base exception for codebase analysis errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ContextError(AnalysisError):
    """Error related to context building or management."""
    pass


class QueryError(AnalysisError):
    """Error related to query execution."""
    pass


class StorageError(AnalysisError):
    """Error related to storage operations."""
    pass


class ConfigurationError(AnalysisError):
    """Error related to configuration."""
    pass


def with_error_handling(
    fallback_return: Any = None,
    reraise: bool = False,
    log_errors: bool = True
) -> Callable:
    """
    Decorator for robust error handling in analysis operations.
    
    Args:
        fallback_return: Value to return if function fails
        reraise: Whether to reraise the exception after handling
        log_errors: Whether to log errors
        
    Returns:
        Decorated function with error handling
    """
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = project_logger
            
            try:
                return func(*args, **kwargs)
                
            except AnalysisError as e:
                if log_errors:
                    logger.error(f"{func.__name__} failed: {e}")
                    if e.details:
                        logger.debug(f"Error details: {e.details}")
                
                if reraise:
                    raise
                return fallback_return
                
            except Exception as e:
                if log_errors:
                    logger.error(f"{func.__name__} failed with unexpected error: {e}")
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                
                if reraise:
                    # Wrap in AnalysisError for consistency
                    raise AnalysisError(f"Unexpected error in {func.__name__}: {str(e)}") from e
                
                return fallback_return
        
        return wrapper
    return decorator


def safe_execute(
    operation: Callable,
    error_message: str = "Operation failed",
    fallback_return: Any = None,
    max_retries: int = 0,
    logger: Optional[Any] = None
) -> Any:
    """
    Safely execute an operation with optional retries.
    
    Args:
        operation: Function to execute
        error_message: Custom error message
        fallback_return: Value to return on failure
        max_retries: Maximum number of retry attempts
        logger: Logger instance to use
        
    Returns:
        Result of operation or fallback_return
    """
    if logger is None:
        logger = project_logger
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return operation()
            
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries:
                logger.warning(f"{error_message} (attempt {attempt + 1}/{max_retries + 1}): {e}")
            else:
                logger.error(f"{error_message} (final attempt): {e}")
    
    # All attempts failed
    if isinstance(last_exception, AnalysisError):
        raise last_exception
    else:
        raise AnalysisError(error_message) from last_exception


class ErrorCollector:
    """
    Collects errors during batch operations.
    
    Useful for operations that process multiple items where you want
    to continue processing even if some items fail.
    """
    
    def __init__(self, logger: Optional[Any] = None):
        self.errors: list[tuple[str, Exception]] = []
        self.logger = logger or project_logger
    
    def try_execute(self, operation: Callable, operation_name: str, *args, **kwargs) -> Any:
        """
        Try to execute an operation, collecting any errors.
        
        Args:
            operation: Function to execute
            operation_name: Name for error reporting
            *args, **kwargs: Arguments for the operation
            
        Returns:
            Result of operation or None if failed
        """
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            self.errors.append((operation_name, e))
            self.logger.warning(f"Operation '{operation_name}' failed: {e}")
            return None
    
    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0
    
    def get_error_summary(self) -> str:
        """Get a summary of all collected errors."""
        if not self.errors:
            return "No errors"
        
        summary_parts = [f"Collected {len(self.errors)} errors:"]
        for operation_name, error in self.errors:
            summary_parts.append(f"  - {operation_name}: {error}")
        
        return "\n".join(summary_parts)
    
    def raise_if_errors(self, message: str = "Operations completed with errors") -> None:
        """Raise an exception if any errors were collected."""
        if self.errors:
            details = {
                "error_count": len(self.errors),
                "errors": [(name, str(error)) for name, error in self.errors]
            }
            raise AnalysisError(message, details=details)


class GracefulFailure:
    """
    Context manager for graceful failure handling.
    
    Allows operations to continue with reduced functionality when
    non-critical components fail.
    """
    
    def __init__(self, 
                 component_name: str,
                 logger: Optional[Any] = None,
                 suppress_exceptions: bool = True):
        self.component_name = component_name
        self.logger = logger or project_logger
        self.suppress_exceptions = suppress_exceptions
        self.failed = False
        self.error: Optional[Exception] = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.failed = True
            self.error = exc_val
            
            self.logger.warning(f"Component '{self.component_name}' failed gracefully: {exc_val}")
            
            if self.suppress_exceptions:
                return True  # Suppress the exception
        
        return False
    
    def is_available(self) -> bool:
        """Check if the component is available (didn't fail)."""
        return not self.failed
    
    def get_error(self) -> Optional[Exception]:
        """Get the error that caused the failure."""
        return self.error
