from langchain_core.prompts import ChatPromptTemplate

from core.prompt.prompt_template_adapters.base_prompt_template_adapter import *
from utils.logs.logging_utils import logger


class ChatPromptTemplateAdapter(BasePromptTemplateAdapter):
    """
    Adapter for LangChain's ChatPromptTemplate.

    This adapter wraps a LangChain ChatPromptTemplate instance and adapts it to the unified interface
    defined by BasePromptTemplateAdapter. It is responsible for generating the final prompt text
    based on the provided keyword arguments. This ensures that chat-based prompt templates can be
    formatted consistently with other prompt types.
    
    Attributes:
        prompt_template (ChatPromptTemplate): The LangChain ChatPromptTemplate instance used for formatting.
    """

    def __init__(self, prompt_template: ChatPromptTemplate):
        """
        Initializes the ChatPromptTemplateAdapter with the given ChatPromptTemplate.

        Args:
            prompt_template (ChatPromptTemplate): An instance of LangChain's ChatPromptTemplate.

        Raises:
            TypeError: If the provided prompt_template is not an instance of ChatPromptTemplate.
        """
        if not isinstance(prompt_template, ChatPromptTemplate):
            logger.error("Invalid type for prompt_template: %s. Expected ChatPromptTemplate.", type(prompt_template))
            raise TypeError("prompt_template must be an instance of ChatPromptTemplate.")
        
        self.prompt_template = prompt_template
        logger.debug("%s initialized with ChatPromptTemplate: %s", self.__class__.__name__, prompt_template)


    def format(self, **kwargs) -> str:
        """
        Generates the final text of the prompt using the underlying ChatPromptTemplate.

        This method formats the chat prompt template with the provided keyword arguments,
        logging key steps for debugging purposes. Any exceptions during formatting are logged
        and re-raised.

        Args:
            **kwargs: Keyword arguments to be substituted into the chat prompt template.

        Returns:
            str: The final formatted prompt text.

        Raises:
            Exception: Propagates any exception raised during the formatting process.
        """
        logger.info("Formatting prompt using %s with arguments: %s", self.__class__.__name__, kwargs)
        try:
            prompt_text = self.prompt_template.format(**kwargs)
            logger.debug("Generated prompt text: %s", prompt_text)
            return prompt_text
        except Exception as e:
            logger.error("Error formatting prompt in %s: %s", self.__class__.__name__, e)
            raise
