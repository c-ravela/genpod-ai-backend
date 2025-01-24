from abc import ABC, abstractmethod


class BasePromptAdapter(ABC):
    """
    Abstract base class for all prompt types.
    Requires the implementation of the 'render' method.
    """
    
    @abstractmethod
    def render(self, **kwargs) -> str:
        """
        Generate the final text of the prompt given named arguments.
        """
        pass