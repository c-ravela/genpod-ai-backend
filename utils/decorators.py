from functools import wraps
from utils.logs.logging_utils import logger

def auto_init(init_func):
    """
    Decorator to automatically initialize attributes based on the __init__ parameters.
    """
    @wraps(init_func)
    def wrapper(self, *args, **kwargs):
        try:
            # Log the start of the initialization
            logger.info(f"Initializing {self.__class__.__name__} with args={args}, kwargs={kwargs}")
            
            # Call the original __init__ method
            init_func(self, *args, **kwargs)
            logger.info(f"Called the original __init__ for {self.__class__.__name__}")

            # Get the argument names and default values from the __init__ signature
            init_args = init_func.__code__.co_varnames[1:init_func.__code__.co_argcount]  # Skip `self`
            init_defaults = init_func.__defaults__ or ()
            defaults = dict(zip(init_args[-len(init_defaults):], init_defaults))

            # Assign all provided arguments (positional and keyword)
            provided_args = dict(zip(init_args, args))
            for key, value in {**defaults, **provided_args, **kwargs}.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    logger.debug(f"Set attribute {key}={value!r} on {self.__class__.__name__}")
                else:
                    logger.warning(f"Attribute {key} does not exist on {self.__class__.__name__} and was ignored.")
            
            logger.info(f"Initialization of {self.__class__.__name__} completed successfully.")
        except Exception as e:
            logger.error(f"Error during initialization of {self.__class__.__name__}: {e}", exc_info=True)
            raise

    return wrapper
