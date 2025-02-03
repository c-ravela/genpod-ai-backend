from functools import wraps

from core.decorators.utils import validate_workflow_node_signature
from core.state import BaseState
from core.workflow import BaseWorkFlow
from utils.logs.logging_utils import logger


def route_on_errors(func=None, *, max_error_threshold=3):
    """
    A decorator that checks the state's error count before executing the router function.
    
    If the error count is at or above the threshold, it logs the error details (including the agent's name,
    function name, and decorator name) and raises an exception.
    
    If there are transient errors (error_count > 0 but below the threshold), it logs this information and
    returns the last node.
    
    Otherwise, it calls the wrapped router function and logs the successful execution.
    """
    decorator_name = "route_on_errors"

    def decorator(func):
        func_name = validate_workflow_node_signature(func, decorator_name)

        @wraps(func)
        def wrapper(*args, **kwargs):
            self: BaseWorkFlow = args[0]
            state: BaseState = args[1]
            
            logger.info(
                "[%s] Agent '%s': Executing router function '%s' with state: error_count=%d, last_node='%s', active_node='%s'.",
                decorator_name, self.agent_name, func_name, state.error_count, state.last_node, state.active_node
            )

            if state.error_count >= max_error_threshold:
                error_msg = (
                    f"[{decorator_name}] Agent '{self.agent_name}': "
                    f"Error threshold exceeded: {state.error_count} errors. Halting process."
                )
                logger.error(error_msg)
                raise Exception(error_msg)
            elif state.error_count > 0:
                logger.info(
                    "[%s] Agent '%s': Transient error detected (error_count=%d) in router function '%s'. "
                    "Routing to last node: '%s'.",
                    decorator_name, self.agent_name, state.error_count, func_name, state.last_node
                )
                return state.last_node
            else:
                result = func(*args, **kwargs)
                logger.info(
                    "[%s] Agent '%s': Router function '%s' executed successfully. Routing to node: '%s'.",
                    decorator_name, self.agent_name, func_name, result
                )
                return result
        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)
