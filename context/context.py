from typing import Dict, Optional

from context.agent_context import AgentContext
from context.task_context import TaskContext
from utils.logs.logging_utils import logger


class GenpodContext:
    """
    A singleton context class with fields that are easy to access, update, and retrieve.
    """
    __slots__ = (
       "project_id",
       "microservice_id",
       "session_ids",
       "user_id",
       "project_path",
       "previous_agent",
       "current_agent",
       "current_task",
       "_initialized"
    )
    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Ensure only one instance of the class exists.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.debug("Created a new instance of GenpodContext.")
        return cls._instance

    def __init__(self):
        """Initialize or re-initialize fields if necessary."""
        if not hasattr(self, "_initialized"):

            # Initialize fields
            self.project_id: Optional[int] = None
            self.microservice_id: Optional[int] = None
            self.session_ids: Optional[Dict[str, int]] = None
            self.user_id: Optional[int] = None
            self.project_path:  Optional[str] = None
            self.previous_agent: Optional[AgentContext] = None
            self.current_agent: Optional[AgentContext] = None
            self.current_task: Optional[TaskContext] = None

            # Ensure this is set last to signal the completion of initialization
            self._initialized = True
            logger.info("Initialized GenpodContext fields with default values.")

    def __setattr__(self, name, value):
        """
        Intercept attribute assignments to block direct updates outside initialization.

        Behavior:
        - During initialization (`_initialized` is False), all attribute assignments are allowed.
        - After initialization (`_initialized` is True), direct assignments to fields defined in `__slots__`
        are restricted to enforce controlled updates using the `update` method.

        Rationale:
        - This ensures that fields are updated only through a controlled mechanism (`update`),
        allowing for validation, logging, or any other required logic.
        - Prevents accidental modifications to critical fields by enforcing stricter control
        once the object has been fully initialized.

        Parameters:
            name (str): The name of the attribute being set.
            value: The value to assign to the attribute.

        Raises:
            AttributeError: If a direct assignment is attempted to a restricted field after initialization.

        Examples:
            Allowed during initialization:
                context = GenpodContext()

            Allowed through update method:
                context.update(project_id=123)

            Disallowed direct assignment after initialization:
                context.project_id = 123  # Raises AttributeError
        """
        if getattr(self, "_initialized", False):  # Only enforce restriction if initialized
            if name in self.__slots__ and name != "_initialized":
                logger.warning(
                    f"Direct assignment attempt to '{name}' is blocked. Use the 'update' method instead."
                )
                raise AttributeError(
                    f"Direct assignment to '{name}' is not allowed. Use the 'update' method instead."
                )
        logger.debug(f"Setting attribute '{name}' to '{value}'.")
        super().__setattr__(name, value)
        logger.info(f"Attribute '{name}' successfully set to '{value}'.")

    @classmethod
    def get_context(cls) -> 'GenpodContext':
        """
        Retrieve the singleton instance of the class.

        Returns:
            GenpodContext: The singleton instance.

        Raises:
            Exception: If the singleton instance is not initialized.
        """
        if cls._instance is None:
            logger.error("Attempted to access the GenpodContext instance without initializing it.")
            raise Exception("GenpodContext instance is not initialized.")
        logger.debug("Returning the existing GenpodContext instance.")
        return cls._instance

    def update(self, **kwargs):
        """
        Update multiple fields in the context.
        """
        logger.info(f"Received update request with fields: {kwargs}.")
        for key, value in kwargs.items():
            if key not in self.__slots__ or key == "_initialized":
                logger.error(f"Attempted to update invalid or restricted field '{key}'.")
                raise AttributeError(f"Field '{key}' is invalid or restricted in {self.__class__.__name__}.")
            if key == "current_agent" and hasattr(self, "current_agent"):
                logger.debug(f"Setting 'previous_agent' to '{self.current_agent}' before updating 'current_agent'.")
                object.__setattr__(self, "previous_agent", self.current_agent)
            logger.debug(f"Updating field '{key}' to value '{value}'.")
            # Use `object.__setattr__` to bypass `__setattr__` restrictions
            object.__setattr__(self, key, value)
            logger.info(f"Field '{key}' successfully updated to '{value}'.")

    def get_fields(self):
        """
        Retrieve all fields and their current values as a dictionary.
        """
        fields = {
            slot: getattr(self, slot)
            for slot in self.__slots__
            if slot != "_initialized"  # Exclude internal field
        }
        logger.debug(f"Retrieved fields: {fields}.")
        return fields
