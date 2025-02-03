from typing import Any, Dict, Literal

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableSequence
from langchain_ollama import ChatOllama

from llms.llm import LLM
from utils.logs.logging_utils import logger


class Ollama(LLM[ChatOllama]):
    """Ollama provider implementation for invoking Ollama's language models."""

    provider_name = "ollama"

    def __init__(
        self,
        model: str,
        model_config: Dict[str, Any],
        max_retries: int,
        retry_backoff: float
    ) -> None:
        """
        Initializes the Ollama LLM provider with the specified model and configuration.

        Args:
            model (str): The name of the Ollama model to use.
            model_config (Dict[str, Any]): Configuration settings specific to the model.
        """
        logger.debug(
            "Initializing Ollama provider with model: %s, config: %s, max_retries: %d, retry_backoff: %f",
            model, model_config, max_retries, retry_backoff
        )
        try:
            super().__init__(
                model=model,
                model_config=model_config,
                max_retries=max_retries,
                retry_backoff=retry_backoff
            )
            logger.info("Ollama provider initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize Ollama provider.")
            raise

    @property
    def provider(self) -> str:
        """Return the provider name."""
        logger.debug("Accessing provider name: %s", self.provider_name)
        return self.provider_name

    def _initialize_llm_instance(self) -> ChatOllama:
        """
        Initializes the Ollama LLM instance.

        Returns:
            ChatOllama: The initialized Ollama LLM instance.
        """
        logger.debug("Initializing ChatOllama instance with model: %s", self.model)
        try:
            instance = ChatOllama(model=self.model, **self.model_config)
            logger.info("ChatOllama instance initialized successfully.")
            return instance
        except Exception as e:
            logger.exception("Failed to initialize ChatOllama instance.")
            raise

    def _create_chain(
        self,
        prompt: PromptTemplate,
        response_type: Literal['string', 'json', 'raw']
    ) -> RunnableSequence:
        """
        Create a runnable chain for invoking OpenAI with the desired response format, ensuring usage metadata extraction.

        Args:
            prompt (PromptTemplate): The prompt template to use for the invocation.
            response_type (Literal['string', 'json', 'raw']): The desired output format.

        Returns:
            RunnableSequence: A chain that can invoke the LLM with the specified response format.
        """
        logger.debug(
            "Creating chain with prompt: %s and response type: %s", prompt, response_type
        )
        try:
            # Extract metadata before passing to the parsers
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
        except Exception as e:
            logger.exception("Failed to create chain.")
            raise
