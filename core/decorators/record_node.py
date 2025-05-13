from functools import wraps

from core.decorators.utils import validate_workflow_node_signature
from utils.logger import logger


def record_node(node_name: str = None):
    """
    Decorator to track and update the node transition in an agent's internal state.

    This decorator is intended for workflow node methods. It performs the following tasks:
    
      1. **Before Invocation:**  
         - Captures the current active node from the state as `prev_node`.
         - Sets the current node (provided via `node_name` or defaulting to the decorated function's name)
           as the new active node.
         
      2. **After Completion:**  
         - Executes the wrapped node function.
         - Upon completion, updates the state's `last_node` and `active_node` to the current node,
           indicating that this node has completed processing.

    This ensures that:
      - During execution, any method inspecting the state will see the node in progress as the active node.
      - After execution, subsequent methods will see that the last visited node accurately reflects the completed node.

    **Expected Function Signature:**
    
        def method(self, state: BaseState, *args, **kwargs) -> Any:
            ...

    Where:
      - `self` is the instance of a class (typically a subclass of BaseWorkFlow).
      - `state` is an instance of BaseState (or one of its subclasses).
      - Additional positional and keyword arguments can be provided as needed.

    **Usage Examples:**

    1. **Using the default node name (the function's name):**
       ```python
       @record_node()
       def process_data(self, state):
           # Function implementation here.
           pass
       ```
       In this case, if the function is named "process_data", that will be used as the node name.

    2. **Specifying an explicit node name:**
       ```python
       @record_node("entry")
       def initialize(self, state):
           # Function implementation here.
           pass
       ```
       Here, the node name "entry" is used regardless of the function's actual name.

    Args:
        node_name (str, optional): The name of the node. If not provided, the decorator defaults
            to using the function's name.

    Returns:
        Callable: The decorated function with state tracking enabled.
    
    Note:
        This decorator is designed to be used on instance methods of classes where the first
        argument is `self` and the second argument is a state object of type `BaseState` (or a subclass).
    """
    def decorator(func):
        decorator_name = "record_node"
        func_name = validate_workflow_node_signature(func, decorator_name)

        @wraps(func)
        def wrapper(self, state, *args, **kwargs):
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
