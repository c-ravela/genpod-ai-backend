from abc import ABC, abstractmethod


class IPrompt(ABC):
    """
    Interface for all prompts.
    """

    @abstractmethod
    def get_prompt(self, identifier: str, **kwargs) -> str:
        """
        Retrieves a prompt template based on an identifier and formats it with provided arguments.

        Args:
            identifier (str): The identifier for the prompt template.
            **kwargs: Parameters to format the prompt.

        Returns:
            str: The formatted prompt.
        """
        pass
