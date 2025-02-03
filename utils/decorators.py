from functools import wraps

from utils.logs.logging_utils import logger


def auto_init(init_func):
    """
    Decorator to automatically initialize attributes based on the __init__ parameters.

    This decorator performs the following steps:
      1. Logs the start of initialization with the provided positional and keyword arguments.
      2. Calls the original __init__ method.
      3. Retrieves the parameter names and default values from the __init__ signature.
      4. Iterates over the combination of default values, provided positional arguments, and keyword arguments.
      5. Sets the corresponding attribute on the instance if it exists; otherwise, logs a warning.

    Args:
        init_func (Callable): The original __init__ method to be wrapped.

    Returns:
        Callable: The wrapped __init__ method.
    """
    @wraps(init_func)
    def wrapper(self, *args, **kwargs):
        try:
            # Log the start of the initialization
            logger.debug("Initializing %s with args=%s, kwargs=%s", self.__class__.__name__, args, kwargs)
            
            # Call the original __init__ method
            init_func(self, *args, **kwargs)
            logger.info("Called the original __init__ for %s", self.__class__.__name__)

            init_args = init_func.__code__.co_varnames[1:init_func.__code__.co_argcount]
            init_defaults = init_func.__defaults__ or ()
            defaults = dict(zip(init_args[-len(init_defaults):], init_defaults)) if init_defaults else {}

            provided_args = dict(zip(init_args, args))
            for key, value in {**defaults, **provided_args, **kwargs}.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    logger.debug("Set attribute %s=%r on %s", key, value, self.__class__.__name__)
                else:
                    logger.warning("Attribute %s does not exist on %s and was ignored.", key, self.__class__.__name__)
            
            logger.info("Initialization of %s completed successfully.", self.__class__.__name__)
        except Exception as e:
            logger.error("Error during initialization of %s: %s", self.__class__.__name__, e, exc_info=True)
            raise

    return wrapper

def auto_repr(cls):
    """
    Class decorator that adds an auto-generated __repr__ method to a class.

    The generated __repr__ method returns a string in the format:
        ClassName(field1=value1, field2=value2, ...)
    
    Only attributes that do not start with an underscore (_) are included in the representation.
    This is useful for debugging and logging.

    Args:
        cls (Type): The class to decorate.

    Returns:
        Type: The decorated class with an auto-generated __repr__ method.
    """
    def __repr__(self):
        public_attrs = {key: value for key, value in self.__dict__.items() if not key.startswith('_')}
        attr_str = ", ".join(f"{key}={value!r}" for key, value in public_attrs.items())
        return f"{self.__class__.__name__}({attr_str})"
    
    cls.__repr__ = __repr__
    logger.debug("Auto-generated __repr__ method added to class %s", cls.__name__)
    return cls
