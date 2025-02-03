from functools import wraps

from pydantic import ValidationError

from core.decorators.utils import validate_workflow_node_signature
from core.state import BaseState
from core.workflow import BaseWorkFlow
from utils.logs.logging_utils import logger


def _update_state_on_error(state: BaseState, error_detail: str, exc: Exception) -> None:
    """
    Updates the given state with error details.

    Increments the state's error_count, sets the error_message, and logs the error.

    Args:
        state (BaseState): The workflow state to update.
        error_detail (str): The error detail message to record.
        exc (Exception): The exception that occurred.
    """
    state.error_count += 1
    state.error_message = error_detail
    logger.error(error_detail, exc_info=True)

def handle_errors_and_reset(func):
    """
    A decorator that handles errors by updating the state's error_count and error_message.
    If the decorated function completes successfully, it resets the error state.
    """
    decorator_name = "handle_errors_and_reset"
    func_name = validate_workflow_node_signature(func, decorator_name)

    @wraps(func)
    def wrapper(*args, **kwargs):
        self: BaseWorkFlow = args[0]
        state: BaseState = args[1]

        logger.debug(
            f"[{decorator_name}] Invoking function '{func_name}' for agent '{self.agent_name}' with state: {state}"
        )
        try:
            result = func(*args, **kwargs)

            logger.info(
                f"[{decorator_name}] Function '{func_name}' completed successfully for agent '{self.agent_name}'. Resetting error state."
            )

            state.error_count = 0
            state.error_message = ""
            return result
        except ValidationError as ve:
            state.error_count += 1
            error_detail = (
                f"[{decorator_name}] Pydantic validation error in '{func_name}' "
                f"of '{self.agent_name}': {ve.json()}"
            )

            _update_state_on_error(state, error_detail, ve)
            raise
        except AttributeError as ae:
            error_detail = (
                f"[{decorator_name}] Unrecoverable attribute error in '{func_name}' "
                f"of '{self.agent_name}': {ae}"
            )

            _update_state_on_error(state, error_detail, ae)
            raise
        except RuntimeError as re:
            error_detail = (
                f"[{decorator_name}] Unrecoverable runtime error in '{func_name}' of '{self.agent_name}': {re}"
            )
            
            _update_state_on_error(state, error_detail, re)
            raise
        except Exception as e:
            print(type(e))
            error_detail = (
                f"[{decorator_name}] An error occurred in '{func_name}' "
                f"of '{self.agent_name}': {e}"
            )
            
            _update_state_on_error(state, error_detail, e)
            # Do not re-raise exception, allowing the router to handle retries or alternative routing.
            return state
    return wrapper
