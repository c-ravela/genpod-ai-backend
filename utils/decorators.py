import os
from enum import Enum
from functools import wraps
from pprint import pformat

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

def _unwrap_enums(obj):
    """
    Recursively unwrap enum values from the given object.
    
    - If the object is an instance of an Enum, return its underlying value.
    - If the object is an enum type (a subclass of Enum), return a list of its unwrapped members.
    - Otherwise, process containers (lists, tuples, sets, dicts) recursively.
    """
    if isinstance(obj, Enum):
        return unwrap_enums(obj.value)
    elif isinstance(obj, type) and issubclass(obj, Enum):
        return [unwrap_enums(member) for member in obj]
    elif isinstance(obj, list):
        return [unwrap_enums(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(unwrap_enums(item) for item in obj)
    elif isinstance(obj, set):
        return {unwrap_enums(item) for item in obj}
    elif isinstance(obj, dict):
        return {key: unwrap_enums(value) for key, value in obj.items()}
    return obj

def auto_repr(_cls=None, *, include_private=False):
    """
    Class decorator that adds an auto-generated __repr__ method to a class.
    
    The generated __repr__ method returns a string in the format:
        ClassName(field1=value1, field2=value2, ...)
    
    By default, only attributes that do not start with an underscore (_) are included.
    You can change this behavior by setting `include_private=True` when applying the decorator.
    
    The output format is configurable via environment variables:
      - AUTO_REPR_PRETTY: If truthy, uses a pretty-formatted output (using pformat).
      - AUTO_REPR_UNWRAP_ENUMS: If truthy, enum instances are replaced by their underlying values,
        and enum types are replaced by a list of their unwrapped members.
    
    Args:
        include_private (bool): Whether to include private fields (those starting with '_').
                                Defaults to False.
    
    Returns:
        The decorated class with an auto-generated __repr__ method.
    
    Usage:
        @auto_repr
        class MyClass:
            ...
        
        # or to include private fields:
        @auto_repr(include_private=True)
        class MyClass:
            ...
    """
    use_pretty = os.environ.get("AUTO_REPR_PRETTY", "False").lower() in ("true", "1", "yes")
    unwrap_enums_flag = os.environ.get("AUTO_REPR_UNWRAP_ENUMS", "False").lower() in ("true", "1", "yes")

    def decorator(cls):
        def __repr__(self):
            if include_private:
                attrs = self.__dict__
            else:
                attrs = {key: value for key, value in self.__dict__.items() if not key.startswith('_')}
            
            if unwrap_enums_flag:
                attrs = _unwrap_enums(attrs)
            
            if use_pretty:
                formatted_attrs = pformat(attrs, indent=2, width=80, compact=True)
                return f"{self.__class__.__name__}({formatted_attrs})"
            else:
                attr_str = ", ".join(f"{key}={value!r}" for key, value in attrs.items())
                return f"{self.__class__.__name__}({attr_str})"
        
        cls.__repr__ = __repr__
        logger.debug("Auto-generated __repr__ method added to class %s", cls.__name__)
        return cls

    if _cls is None:
        # Decorator is used with parameters.
        return decorator
    else:
        # Decorator is used without parameters.
        return decorator(_cls)
