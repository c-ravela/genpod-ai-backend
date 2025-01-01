from typing import Optional, Dict
from utils.logs.logging_utils import logger
from context.agent_context import AgentContext
from context.task_context import TaskContext


class GenpodContext:
    """
    A singleton context class with fields that are easy to access, update, and retrieve.
    """
    __slots__ = (
       "project_id",
       "microservice_id",
       "session_id",
       "user_id",
       "project_path",
       "current_agent",
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
        """
        Initialize or re-initialize fields if necessary.
        """
        if not hasattr(self, "_initialized"):
            self._initialized = True  # Mark the instance as initialized

            # Initialize fields
            self.project_id: Optional[int] = None
            self.microservice_id: Optional[int] = None
            self.session_id: Optional[Dict[str, int]] = None
            self.user_id: Optional[int] = None
            self.project_path:  Optional[str] = None
            self.current_agent: Optional[AgentContext] = None
            self.current_task: Optional[TaskContext] = None
            logger.info("Initialized GenpodContext fields with default values.")

    @classmethod
    def get_instance(cls):
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
        for key, value in kwargs.items():
            if not hasattr(self, key):
                logger.error(f"Attempted to update invalid field '{key}'.")
                raise AttributeError(f"Invalid field '{key}' for {self.__class__.__name__}.")
            setattr(self, key, value)
            logger.debug(f"Updated field '{key}' to value '{value}'.")

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
