from abc import ABC, abstractmethod
from os import getcwd, path
from string import Formatter
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from core.prompt.prompt_template_adapters.base_prompt_template_adapter import \
    BasePromptTemplateAdapter
from core.prompt.utils import load_instructions_from_yaml
from utils.logger import logger

GLOBAL_INSTRUCTIONS_PATH = path.join(getcwd(), "prompts", "global_prompt_instructions.yaml")


class BasePrompt(BaseModel, ABC):
    """
    BasePrompt provides basic prompt rendering functionality.

    It integrates with a prompt template adapter (implementing BasePromptTemplateAdapter) to format 
    the core prompt. It automatically loads common instructions from a YAML configuration file and 
    wraps the formatted prompt with these instructions.

    Attributes:
        adapter (BasePromptTemplateAdapter): Adapter instance for formatting the prompt template.
        common_instructions (Dict[str, str]): A dictionary containing common instructions under keys 
                                              'top' and 'bottom'.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    adapter: BasePromptTemplateAdapter
    common_instructions: Dict[str, str] = Field(default_factory=dict, init=False)

    @classmethod
    def load_common_instructions(cls, filepath: str = GLOBAL_INSTRUCTIONS_PATH) -> Dict[str, str]:
        """
        Loads and aggregates common instructions from a YAML configuration file.

        This method delegates file reading and aggregation to `load_instructions_from_yaml`.

        Args:
            filepath (str): The path to the YAML file containing common instructions.

        Returns:
            Dict[str, str]: A dictionary with keys "top" and "bottom" containing the aggregated instructions.

        Raises:
            Exception: Propagates any exception raised during instruction loading.
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
        Initializes the BasePrompt instance with a prompt template adapter and additional parameters.

        Args:
            adapter (BasePromptTemplateAdapter): The adapter used for prompt formatting.
            **kwargs: Additional keyword arguments.

        Raises:
            Exception: Propagates exceptions from loading common instructions.
        """
        logger.debug("Initializing BasePrompt with adapter: %s and extra kwargs: %s", adapter, kwargs)
        super().__init__(adapter=adapter, **kwargs)
        if not self.common_instructions:
            self.common_instructions = self.load_common_instructions()
            logger.debug("Common instructions set to: %s", self.common_instructions)

    @abstractmethod
    def _format_prompt(self, **kwargs: Any) -> str:
        """
        Abstract method to generate the core prompt text.

        Subclasses must implement this method to perform all necessary substitutions in the prompt.

        Args:
            **kwargs: Keyword arguments for prompt formatting.

        Returns:
            str: The fully formatted core prompt text.
        """
        pass

    def wrap_with_common(self, text: str) -> str:
        """
        Wraps the given prompt text with the common top and bottom instructions.

        Args:
            text (str): The core prompt text to be wrapped.

        Returns:
            str: The complete prompt with common instructions appended.
        """
        common_top = self.common_instructions.get("top", "")
        common_bottom = self.common_instructions.get("bottom", "")
        wrapped = f"{common_top}\n{text}\n{common_bottom}".strip()
        logger.debug("Wrapped prompt with common instructions: %s", wrapped)
        return wrapped

    def render(self, **kwargs: Any) -> str:
        """
        Renders the final prompt.

        This method first generates the core prompt text by invoking the subclass's `_format_prompt` 
        method, then escapes any literal curly braces, and finally wraps the result with the common instructions.

        Args:
            **kwargs: Keyword arguments for substituting into the prompt template.

        Returns:
            str: The complete rendered prompt including common instructions.

        Raises:
            Exception: Propagates any exception that occurs during formatting or wrapping.
        """
        logger.info("Rendering prompt with arguments: %s", kwargs)
        try:
            core_text = self._format_prompt(**kwargs)
            logger.debug("Core prompt text generated: %s", core_text)

            # Escape literal curly braces.
            escaped_text = core_text.replace("{", "{{").replace("}", "}}")
            logger.debug("Core prompt text after escaping braces: %s", escaped_text)

            final_prompt = self.wrap_with_common(escaped_text)
            logger.debug("Final rendered prompt: %s", final_prompt)
            return final_prompt
        except Exception as e:
            logger.error("Error rendering prompt: %s", e, exc_info=True)
            raise

    @staticmethod
    def safe_format(template: str, **kwargs: Any) -> str:
        """
        Strictly validates and formats a template string using provided keyword arguments.

        The method ensures that all placeholders in the template have corresponding keys in the provided
        kwargs. If any required key is missing, it raises a ValueError with a detailed message including 
        the missing keys, all expected keys, and the keys that were provided.

        Args:
            template (str): The template string containing placeholders.
            **kwargs: Keyword arguments for populating the template.

        Returns:
            str: The formatted string if all required keys are present.

        Raises:
            ValueError: If one or more required placeholders are missing in the kwargs.
        """
        logger.debug("Starting safe_format on template: '%s' with kwargs: %s", template, kwargs)
        formatter = Formatter()
        # Extract all required keys from the template.
        required_keys = {field_name for _, field_name, _, _ in formatter.parse(template) if field_name}
        logger.debug("Extracted required keys: %s", required_keys)

        missing_keys = required_keys - set(kwargs.keys())
        if missing_keys:
            error_message = (
                f"Template formatting error: Missing required keys: {', '.join(sorted(missing_keys))}. "
                f"Expected keys: {', '.join(sorted(required_keys))}. "
                f"Provided keys: {', '.join(sorted(kwargs.keys()))}. "
                "Please ensure all required keys are included."
            )
            logger.error(error_message)
            raise ValueError(error_message)

        result = template.format(**kwargs)
        logger.debug("Formatted template result: '%s'", result)
        return result
