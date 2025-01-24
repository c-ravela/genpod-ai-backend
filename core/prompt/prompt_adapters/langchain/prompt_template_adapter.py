from langchain_core.prompts import PromptTemplate

from core.prompt import PromptAdapter
from utils.logs.logging_utils import logger


class PromptTemplateAdapter(PromptAdapter):
    """
    Adapter for LangChain's PromptTemplate.
    """

    def __init__(self, prompt_template: PromptTemplate):
        if not isinstance(prompt_template, PromptTemplate):
            logger.error(f"Invalid type for prompt_template: {type(prompt_template)}. Expected PromptTemplate.")
            raise TypeError("prompt_template must be an instance of PromptTemplate.")
        
        self.prompt_template = prompt_template
        logger.debug(f"{self.__class__.__name__} initialized with PromptTemplate.")

    def render(self, **kwargs) -> str:
        logger.info(f"Rendering PromptTemplateAdapter with arguments: {kwargs}")
        try:
            prompt_text = self.prompt_template.format(**kwargs)
            logger.debug(f"Generated prompt text: {prompt_text}")
            return prompt_text
        except Exception as e:
            logger.error(f"Error rendering prompt: {e}")
            raise
