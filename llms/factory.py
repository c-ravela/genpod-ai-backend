from llms.anthropic_llm import Anthropic
from llms.llm import LLM
from llms.ollama_llm import Ollama
from llms.openai_llm import OpenAI


def llm_factory(provider: str, model: str, model_config: dict, max_retries: int, retry_backoff: float) -> LLM:
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
    if provider == "openai":
        return OpenAI(model, model_config, max_retries, retry_backoff)
    elif provider == "ollama":
        return Ollama(model, model_config, max_retries, retry_backoff)
    elif provider == "anthropic":
        return Anthropic(model, model_config, max_retries, retry_backoff)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
