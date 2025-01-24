from abc import ABC, abstractmethod
from typing import Dict

from core.prompt import IPrompt


class BasePrompt(IPrompt, ABC):
    """
    Abstract base class for all prompts, implementing common functionalities.
    """

    def __init__(self) -> None:
        self.prompts: Dict[str, str] = self.load_prompts()

    @abstractmethod
    def load_prompts(self) -> Dict[str, str]:
        """
        Loads prompt templates.

        Returns:
            Dict[str, str]: A dictionary mapping identifiers to prompt templates.
        """
        pass

    def get_prompt(self, identifier: str, **kwargs) -> str:
        prompt_template = self.prompts.get(identifier)
        if not prompt_template:
            raise ValueError(f"Prompt '{identifier}' not found.")
        return prompt_template.format(**kwargs)
