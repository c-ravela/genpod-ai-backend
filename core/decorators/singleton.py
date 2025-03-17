from functools import wraps
from typing import Self, Type, TypeVar


class Singleton:
    """
    An abstract base class to promote type hinting for the singleton pattern.

    This class is provided solely to signal that a class implements a type-hinted 
    `get_instance` class method. It does not enforce any singleton behavior by itself.

    Note:
        To achieve true singleton behavior, the class must also be decorated with the
        `@singleton` decorator.

    Usage:
        @singleton
        class MyClass(Singleton):
            def __init__(self, param1: str, param2: str):
                self.param1 = param1
                self.param2 = param2

        # Create the singleton instance using the constructor:
        instance = MyClass(param1='foo', param2='bar')

        # Retrieve the same instance later:
        same_instance = MyClass.get_instance()
        assert instance is same_instance
    """
    @classmethod
    def get_instance(cls) -> Self:
        """
        Returns the singleton instance of the class.

        Raises:
            RuntimeError: If the method is not implemented by the subclass.
        """
        raise RuntimeError("Subclass has to implement this")


T = TypeVar("T", bound=Singleton)


def singleton(cls: Type[T]) -> Type[T]:
    """
    A decorator that transforms a class into a singleton.

    The first time the class is instantiated, the instance is created and __init__ is called.
    Subsequent instantiations return the same instance without re-calling __init__.

    A type-hinted `get_instance` class method is also injected into the class to retrieve
    the singleton instance. This method is intended to match the interface declared in the
    `Singleton` abstract base class.

    Note:
        The `Singleton` base class is provided solely to promote type hinting of the 
        `get_instance` method and does not implement any singleton behavior on its own.
        To get true singleton behavior, be sure to decorate your class with `@singleton`
        in addition to (optionally) inheriting from `Singleton` for type checking.

    Usage:
        @singleton
        class MyClass(Singleton):
            def __init__(self, param1: str, param2: str):
                self.param1 = param1
                self.param2 = param2

        # Create the singleton instance using the constructor:
        instance = MyClass(param1='foo', param2='bar')

        # Retrieve the same instance later:
        same_instance = MyClass.get_instance()
        assert instance is same_instance
    """
    instance: T = None
    initialized = False

    original_init = cls.__init__
    original_new = cls.__new__

    @wraps(original_new)
    def new(cls, *args, **kwargs):
        nonlocal instance, initialized
        # If the instance already exists, return it without calling __init__
        if instance is not None:
            return instance

        # Create the instance
        if original_new is object.__new__:
            instance_local = object.__new__(cls)
        else:
            instance_local = original_new(cls, *args, **kwargs)
        instance = instance_local 
        return instance

    cls.__new__ = new

    @wraps(original_init)
    def new_init(self, *args, **kwargs):
        nonlocal initialized
        # Call __init__ only if it has not been called before
        if not initialized:
            original_init(self, *args, **kwargs)
            initialized = True

    cls.__init__ = new_init

    @classmethod
    @wraps(original_init)
    def get_instance(cls: Type[T]) -> T:
        """
        Returns the singleton instance of the class.

        Raises:
            Exception: If the singleton instance has not been created yet.
                       This means the constructor must be called at least once before calling get_instance().
        """
        nonlocal instance
        if instance is None:
            raise Exception(
                f"Singleton instance not created yet for class '{cls.__name__}'. "
                "Please create an instance using the constructor first before calling get_instance()."
            )
        return instance

    cls.get_instance = get_instance
    return cls
