from inspect import _empty, signature

from core.state import BaseState
from core.workflow import BaseWorkFlow
from utils.logs.logging_utils import logger


def validate_workflow_node_signature(func, decorator_name: str):
    """
    Validates that the given function's signature is appropriate for a workflow node method.
    
    The function must have at least two parameters: 'self' and 'state', where:
      - The first parameter is annotated as a subclass of BaseWorkFlow.
      - The second parameter is annotated as a subclass of BaseState.
    
    Logs an error and raises a TypeError if any of these conditions are not met.
    
    Args:
        func (Callable): The function to validate.
        decorator_name (str): The name of the decorator using this validation.
    
    Returns:
        str: The name of the function.
    """
    func_name = func.__name__
    sig_obj = signature(func)
    params = list(sig_obj.parameters.values())

    if len(params) < 2:
        logger.error(
            f"[{decorator_name}] The function '{func_name}' must have at least two parameters (self, state)"
        )
        raise TypeError(
            f"[{decorator_name}] The function '{func_name}' must have at least two parameters (self, state)"
        )

    if params[0].annotation is not _empty:
        if not issubclass(params[0].annotation, BaseWorkFlow):
            logger.error(
                f"[{decorator_name}] In function '{func_name}', the first parameter must be a subclass of BaseWorkFlow, "
                f"got {params[0].annotation}"
            )
            raise TypeError(
                f"[{decorator_name}] In function '{func_name}', the first parameter must be a subclass of BaseWorkFlow, "
                f"got {params[0].annotation}"
            )

    if params[1].annotation is not _empty:
        if not issubclass(params[1].annotation, BaseState):
            logger.error(
                f"[{decorator_name}] In function '{func_name}', the second parameter must be a subclass of BaseState, "
                f"got {params[1].annotation}"
            )
            raise TypeError(
                f"[{decorator_name}] In function '{func_name}', the second parameter must be a subclass of BaseState, "
                f"got {params[1].annotation}"
            )

    return func_name
