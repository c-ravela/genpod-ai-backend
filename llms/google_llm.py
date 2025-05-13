from typing import Any, Dict, Literal

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableSequence
from langchain_google_genai import ChatGoogleGenerativeAI

from llms.llm import LLM
from utils.logger import logger


class GoogleGenerativeAI(LLM[ChatGoogleGenerativeAI]):
    """Google provider implementation for invoking Google's generative AI models."""

    provider_name = "google"

    def __init__(
        self,
        model: str,
        model_config: Dict[str, Any],
        max_retries: int,
        retry_backoff: float
    ) -> None:
        """
        Initializes the Google generative AI provider with the specified model and configuration.

        Args:
            model (str): The name or ID of the Google GenAI model to use.
            model_config (Dict[str, Any]): Configuration settings specific to the Google model.
            max_retries (int): Maximum number of retry attempts.
            retry_backoff (float): Initial backoff time in seconds.
        """
        logger.debug(
            "Initializing GoogleGenerativeAI provider with model: %s, config: %s, max_retries: %d, retry_backoff: %f",
            model, model_config, max_retries, retry_backoff
        )
        try:
            super().__init__(
                model=model,
                model_config=model_config,
                max_retries=max_retries,
                retry_backoff=retry_backoff
            )
            logger.info("GoogleGenerativeAI provider initialized successfully.")
        except Exception:
            logger.exception("Failed to initialize GoogleGenerativeAI provider.")
            raise

    @property
    def provider(self) -> str:
        """Return the provider name."""
        name = self.provider_name
        logger.debug("Accessing provider name: %s", name)
        return name

    def _initialize_llm_instance(self) -> ChatGoogleGenerativeAI:
        """
        Initializes the ChatGoogleGenerativeAI LLM instance.

        Returns:
            ChatGoogleGenerativeAI: The initialized Google GenAI instance.
        """
        logger.debug("Initializing ChatGoogleGenerativeAI instance with model: %s", self.model)
        try:
            instance = ChatGoogleGenerativeAI(model=self.model, **self.model_config)
            logger.info("ChatGoogleGenerativeAI instance initialized successfully.")
            return instance
        except Exception:
            logger.exception("Failed to initialize ChatGoogleGenerativeAI instance.")
            raise

    def _create_chain(
        self,
        prompt: PromptTemplate,
        response_type: Literal['string', 'json', 'raw']
    ) -> RunnableSequence:
        """
        Create a runnable chain for invoking the Google model with desired response format,
        ensuring usage metadata extraction.

        Args:
            prompt (PromptTemplate): The prompt template to use for the invocation.
            response_type (Literal['string', 'json', 'raw']): The desired output format.

        Returns:
            RunnableSequence: A chain configured for the specified response type.
        """
        logger.debug(
            "Creating chain with prompt: %s and response type: %s", prompt, response_type
        )
        try:
            base_chain = prompt | self._llm_instance | self._extract_usage_metadata
            logger.debug("Base chain created successfully.")

            if response_type == 'string':
                final_chain = base_chain | StrOutputParser()
                logger.info("Chain configured for string response type.")
            elif response_type == 'json':
                final_chain = base_chain | JsonOutputParser()
                logger.info("Chain configured for JSON response type.")
            else:
                final_chain = base_chain
                logger.info("Chain configured for raw response type.")

            return final_chain
        except Exception:
            logger.exception("Failed to create chain.")
            raise
