from typing import Any, Dict

from llms.llm import LLM, LLMMeta
from utils.logs.logging_utils import logger


def llm_factory(
    provider: str,
    model: str,
    model_config: Dict[str, Any],
    max_retries: int,
    retry_backoff: float
) -> LLM:
    """
    Factory function to return the appropriate LLM subclass based on the provider.
    
    Args:
        provider (str): The name of the LLM provider (e.g., "openai", "ollama").
        model (str): The model name.
        model_config (dict): The model-specific configuration.
    
    Returns:
        LLM: An instance of the appropriate LLM subclass.
    
    Raises:
        ValueError: If the provider is unsupported.
    """
    logger.debug(
        "Attempting to create LLM instance with provider: %s, model: %s, "
        "model_config: %s, max_retries: %d, retry_backoff: %f",
        provider, model, model_config, max_retries, retry_backoff
    )

    try:
        # Get the appropriate class for the specified provider
        llm_class = LLMMeta.get_provider(provider)
        if not llm_class:
            logger.error("Unsupported LLM provider: %s", provider)
            raise ValueError(f"Unsupported LLM provider: {provider}")

        logger.debug("Found LLM class for provider: %s", provider)

        # Instantiate the LLM subclass
        llm_instance = llm_class(
            model=model,
            model_config=model_config,
            max_retries=max_retries,
            retry_backoff=retry_backoff
        )

        logger.info(
            "Successfully created LLM instance for provider: %s, model: %s", provider, model
        )
        return llm_instance

    except ValueError as ve:
        logger.exception("Failed to create LLM instance due to an invalid provider.")
        raise ve

    except Exception as e:
        logger.exception("Unexpected error occurred while creating LLM instance.")
        raise e
