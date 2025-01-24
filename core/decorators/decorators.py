# agents/base/decorators.py

from functools import wraps
from typing import Any, Callable

from utils.logs.logging_utils import logger


def node_handler(node_name: str) -> Callable:
    """
    Decorator to handle logging and exception management for node methods.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, state: Any) -> Any:
            logger.info(f"{self.agent_name}: Entering node '{node_name}'.")
            try:
                result = func(self, state)
                logger.info(f"{self.agent_name}: Successfully executed node '{node_name}'.")
                return result
            except Exception as e:
                logger.error(f"{self.agent_name}: Error in node '{node_name}': {e}", exc_info=True)
                self.state['has_error_occured'] = True
                self.state['error_message'] = str(e)
                self.add_message("SYSTEM", f"{self.agent_name}: {self.state['error_message']}")
                return self.state
        return wrapper
    return decorator
