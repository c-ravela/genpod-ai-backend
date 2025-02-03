from functools import wraps

from core.decorators.utils import validate_workflow_node_signature
from core.state import BaseState
from core.workflow import BaseWorkFlow
from utils.logs.logging_utils import logger


def record_node(node_name: str = None):
    """
    Decorator to track and update the node transition in an agent's internal state.

    This decorator is intended to be used on workflow node methods.
    It updates the state's `last_node` and `active_node` fields at two points:
    
    1. **Before Invocation:**  
        - The current active node (if any) is stored as the previous node in `last_node`.
        - The current node (specified by `node_name` or the function's name) is set as the new `active_node`.
        
    2. **After Completion:**  
        - The node function is executed.
        - Once finished, the state's `last_node` is updated to the current node, and
        `active_node` is set to the current node as well. This signals that the node has completed.
    
    This ensures that:
      - During execution, any method that inspects the state will see the node in progress as the active node.
      - After execution, any subsequent method (even if not decorated) will find that the last visited node accurately reflects the node that just finished.
    
    Args:
        node_name (str, optional): The name of the node. If not provided, the function name is used.

    Returns:
        Callable: A decorated function with state tracking enabled.
    """
    def decorator(func):
        
        decorator_name = "record_node"
        func_name = validate_workflow_node_signature(func, decorator_name)

        @wraps(func)
        def wrapper(self: BaseWorkFlow, state: BaseState, *args, **kwargs):
            curr_node = node_name or func.__name__
            prev_node = state.active_node

            logger.info(
                "[%s] Agent '%s': Entering function '%s' as node '%s'. Previous active node was '%s'.",
                decorator_name, self.agent_name, func_name, curr_node, prev_node
            )

            # **Before invocation:** Set the active node to the current node.
            # This indicates that a new node is now in progress.
            state.last_node = prev_node
            state.active_node = curr_node

            # Invoke the node function.
            result = func(self, state, *args, **kwargs)

            # **After completion:** Update the state so that the current node is recorded as finished.
            # Both 'last_node' and 'active_node' are updated to reflect the node that just executed.
            state.last_node = curr_node
            state.active_node = curr_node

            logger.info(
                "[%s] Agent '%s': Exiting function '%s' from node '%s'. Updated last_node and active_node to '%s'.",
                decorator_name, self.agent_name, func_name, curr_node, curr_node
            )
            return result
        return wrapper
    return decorator
