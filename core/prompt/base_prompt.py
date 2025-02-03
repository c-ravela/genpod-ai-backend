from abc import ABC, abstractmethod
from os import getcwd, path
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from core.prompt.prompt_template_adapters.base_prompt_template_adapter import *
from core.prompt.utils import load_instructions_from_yaml
from utils.logs.logging_utils import logger

GLOBAL_INSTRUCTIONS_PATH = path.join(getcwd(), "prompts", "global_prompt_instructions.yaml")


class BasePrompt(BaseModel, ABC):
    """
    BasePrompt provides basic prompt rendering functionality.

    This class integrates with a prompt template adapter that implements the 
    BasePromptTemplateAdapter interface. It automatically loads common 
    instructions from a separate YAML configuration file and prepends them to 
    the final prompt text.

    Attributes:
        adapter (BasePromptTemplateAdapter): An adapter instance that formats the prompt template.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    adapter: BasePromptTemplateAdapter
    common_instructions: Dict[str, str] = Field(default_factory=dict, init=False)

    @classmethod
    def load_common_instructions(cls, filepath: str = GLOBAL_INSTRUCTIONS_PATH) -> Dict[str, str]:
        """
        Loads and aggregates common instructions from a YAML configuration file.
        Delegates the actual file reading and aggregation to load_instructions_from_yaml().
        
        Args:
            filepath (str): The path to the YAML file containing common instructions.
        
        Returns:
            dict: A dictionary with keys "top" and "bottom" containing the aggregated common instructions.
        """
        logger.info("Loading common instructions from file: %s", filepath)
        try:
            instructions = load_instructions_from_yaml(filepath)
            logger.debug("Common instructions loaded: %s", instructions)
            return instructions
        except Exception as e:
            logger.error("Failed to load common instructions from %s: %s", filepath, e, exc_info=True)
            raise

    def __init__(
        self,
        *,
        adapter: BasePromptTemplateAdapter,
        **kwargs: Any
    ):
        """
        Initializes the BasePrompt instance with explicit typed parameters.

        Args:
            adapter (BasePromptTemplateAdapter): The prompt template adapter used for formatting.

        Raises:
            Exception: Propagates exceptions from loading common instructions.
        """
        logger.info("Initializing BasePrompt with adapter: %s and extra kwargs: %s", adapter, kwargs)
        super().__init__(adapter=adapter, **kwargs)
        if not self.common_instructions:
            self.common_instructions = self.load_common_instructions()
            logger.debug("Common instructions set to: %s", self.common_instructions)

    @abstractmethod
    def _format_prompt(self, **kwargs: Any) -> str:
        """
        Abstract method that generates the core prompt text.
        Subclasses must implement this to return the prompt text with all substitutions performed.
        
        Args:
            **kwargs: Keyword arguments for prompt formatting.
        
        Returns:
            str: The core prompt text.
        """
        pass

    def wrap_with_common(self, text: str) -> str:
        """
        Wraps the given text with the common instructions.
        
        Args:
            text (str): The prompt text to be wrapped.
            
        Returns:
            str: The prompt text wrapped with common top and bottom instructions.
        """
        common_top = self.common_instructions.get("top", "")
        common_bottom = self.common_instructions.get("bottom", "")
        wrapped = f"{common_top}\n{text}\n{common_bottom}".strip()
        logger.debug("Wrapped text with common instructions: %s", wrapped)
        return wrapped

    def render(self, **kwargs: Any) -> str:
        """
        Renders the final prompt by calling the subclass's _format_prompt method to generate
        the core prompt text, then replacing literal braces (to escape them), and finally wrapping
        the result with the common instructions.

        Args:
            **kwargs: Keyword arguments for substitution into the prompt template.
        
        Returns:
            str: The complete rendered prompt, including common instructions.
        """
        logger.info("Rendering prompt with arguments: %s", kwargs)
        try:
            core_text = self._format_prompt(**kwargs)
            logger.debug("Core prompt text before escaping: %s", core_text)

            # Replace literal curly braces with escaped versions.
            core_text = core_text.replace("{", "{{").replace("}", "}}")
            logger.debug("Core prompt text after escaping: %s", core_text)

            final_prompt = self.wrap_with_common(core_text)
            logger.debug("BasePrompt rendered: %s", final_prompt)
            return final_prompt
        except Exception as e:
            logger.error("Error rendering prompt: %s", e, exc_info=True)
            raise
