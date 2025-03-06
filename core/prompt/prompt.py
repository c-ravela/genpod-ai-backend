from typing import Any

from core.prompt.base_prompt import BasePrompt
from utils.logs.logging_utils import logger


class Prompt(BasePrompt):
    """
    Prompt is a concrete implementation of BasePrompt that simply delegates formatting
    to the adapter. Use this class when no additional wrapping (like RAG instructions) is needed.
    """
    def _format_prompt(self, **kwargs: Any) -> str:
        logger.info("Formatting prompt in Prompt with kwargs: %s", kwargs)
        result = self.adapter.format(**kwargs)
        logger.debug("Prompt _format_prompt result: %s", result)
        return result
