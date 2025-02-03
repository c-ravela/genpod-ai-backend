from abc import ABC, abstractmethod
from typing import Any

from utils.logs.logging_utils import logger


class BasePromptTemplateAdapter(ABC):
    """
    Abstract base class for all prompt template adapters.
    
    This class defines a common interface for converting external prompt templates
    into a unified format. Subclasses must implement the 'format' method, which is
    responsible for generating the final text of the prompt based on the provided
    named arguments.
    
    Implementations should include appropriate logging to aid in debugging and to
    trace the prompt formatting process.
    """
    
    @abstractmethod
    def format(self, **kwargs: Any) -> str:
        """
        Generate the final text of the prompt given named arguments.
        
        This method must be implemented by all concrete subclasses. It should use the
        provided keyword arguments to format the underlying prompt template and return
        the complete prompt text.
        
        Implementations are encouraged to log key events, such as the start of the formatting
        process and any important parameter values, to help with debugging.
        
        Args:
            **kwargs: Keyword arguments to be substituted into the prompt template.
        
        Returns:
            str: The final formatted prompt text.
        
        Raises:
            NotImplementedError: This method must be overridden in a subclass.
        """
        logger.debug("%s.format called with arguments: %s", self.__class__.__name__, kwargs)
        raise NotImplementedError("Subclasses must implement the 'format' method.")
