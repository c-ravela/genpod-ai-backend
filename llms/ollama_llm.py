from typing import Any, Dict, Literal

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableSequence
from langchain_ollama import ChatOllama

from llms.llm import LLM


class Ollama(LLM[ChatOllama]):
    """Ollama provider implementation for invoking Ollama's language models."""

    def __init__(self, model: str, model_config: Dict[str, Any], max_retries: int, retry_backoff: float) -> None:
        """
        Initializes the Ollama LLM provider with the specified model and configuration.

        Args:
            model (str): The name of the Ollama model to use.
            model_config (Dict[str, Any]): Configuration settings specific to the model.
        """
        super().__init__(provider="ollama", model=model, model_config=model_config, llm_class=ChatOllama, max_retries=max_retries, retry_backoff=retry_backoff)

    def _create_chain(self, prompt: PromptTemplate, response_type: Literal['string', 'json', 'raw']) -> RunnableSequence:
        """
        Create a runnable chain for invoking OpenAI with the desired response format, ensuring usage metadata extraction.

        Args:
            prompt (PromptTemplate): The prompt template to use for the invocation.
            response_type (Literal['string', 'json', 'raw']): The desired output format.

        Returns:
            RunnableSequence: A chain that can invoke the LLM with the specified response format.
        """
        # Extract metadata before passing to the parsers
        base_chain = prompt | self._llm_instance | super().extract_usage_metadata

        if response_type == 'string':
            return base_chain | StrOutputParser()
        elif response_type == 'json':
            return base_chain | JsonOutputParser()
        else:
            return base_chain
