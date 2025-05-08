import json
from abc import ABC, ABCMeta, abstractmethod
from dataclasses import dataclass
from time import sleep
from typing import Any, Dict, Generic, Literal, Type, TypeVar, Union

from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableSequence
from pydantic import BaseModel, ValidationError

from core.prompt import BasePrompt
from llms.llm_metrics_callback import *
from models import AdditionalInfoRequest
from utils.decorators import auto_repr
from utils.logger import logger

TLLMInstance = TypeVar('TLLMInstance')
TResponse = TypeVar('TResponse', bound=BaseModel)


@dataclass
class LLMOutput(Generic[TResponse]):
    """Represents the output of a language model invocation, including response and metrics."""
    response: TResponse
    token_usage: TokenUsage


class LLMMeta(ABCMeta):
    """Metaclass for registering LLM providers."""

    _registry = {}

    def __new__(cls, name, bases, attrs):
        logger.debug("Creating a new class with LLMMeta: %s", name)
        new_class = super().__new__(cls, name, bases, attrs)
        provider = attrs.get('provider_name')
        if provider:
            cls._registry[provider] = new_class
            logger.info("Registered LLM provider: %s", provider)
        return new_class

    @classmethod
    def get_provider(cls, provider_name: str):
        """Gets a registered LLM provider by name"""
        logger.debug("Looking up provider: %s", provider_name)
        provider_class = cls._registry.get(provider_name)
        if provider_class:
            logger.info("Found provider: %s", provider_name)
        else:
            logger.warning("Provider not found: %s", provider_name)
        return provider_class


@auto_repr
class LLM(ABC, Generic[TLLMInstance], metaclass=LLMMeta):
    """Abstract base class for different LLM (Large Language Model) providers."""

    def __init__(
        self,
        model: str,
        model_config: Dict[str, Any],
        max_retries: int,
        retry_backoff: float
    ) -> None:
        """
        Initializes the LLM with the given provider, model, and configuration, along with retry mechanism defaults.
        """
        logger.debug(
            "Initializing LLM with model: %s, model_config: %s, max_retries: %d, retry_backoff: %f",
            model, model_config, max_retries, retry_backoff
        )
        self.model = model
        self.model_config = model_config
        self._callbacks = []
        self._llm_instance = self._initialize_llm_instance()
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._current_retry_backoff = self._retry_backoff
        self._last_metrics = TokenUsage()
        logger.info("LLM initialized successfully.")

    @property
    @abstractmethod
    def provider(self) -> str:
        """Return the provider name."""
        pass

    @abstractmethod
    def _initialize_llm_instance(self) -> TLLMInstance:
        """Initialize the LLM instance. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _create_chain(
        self,
        prompt: PromptTemplate,
        response_type: Literal['string', 'json', 'raw']
    ) -> RunnableSequence:
        """Create a runnable chain for invoking the LLM. Must be implemented by provider classes."""
        pass

    def invoke_with_pydantic_model(
        self,
        prompt: BasePrompt,
        prompt_inputs: Dict[str, Any],
        response_model: Type[TResponse]
    ) -> LLMOutput[Union[TResponse, AdditionalInfoRequest]]:
        """
        Invoke the LLM chain and return the response, parsing it into a structured model.

        If a response_model is provided, this method first attempts to parse the LLM's response using that model.
        If that fails, it then attempts to parse the response as an AdditionalInfoRequest.
        
        This method uses a retry mechanism as implemented in __invoke_with_retry.
        
        Returns:
            LLMOutput containing either a response of type TResponse or an AdditionalInfoRequest.
        """
        logger.debug("Invoking LLM with structured model response.")
        return self.__invoke_with_retry(prompt, prompt_inputs, 'json', response_model)

    def invoke(
        self,
        prompt: BasePrompt,
        prompt_inputs: Dict[str, Any],
        response_type: Literal['string', 'json', 'raw'] = 'raw'
    ) -> LLMOutput[Union[str, dict, AIMessage, AdditionalInfoRequest]]:
        """
        Invoke the LLM chain and return the response in the specified format.
        
        If the LLM output does not match the expected type, it will attempt to parse it as an AdditionalInfoRequest.
        
        Expected method signature:
            def invoke(self, prompt: BasePrompt, prompt_inputs: Dict[str, Any],
                    response_type: Literal['string', 'json', 'raw'] = 'raw') -> LLMOutput[Union[str, dict, AIMessage, AdditionalInfoRequest]]:
        
        Returns:
            LLMOutput containing either the raw response (string, dict, or AIMessage) or an AdditionalInfoRequest.
        """
        logger.debug("Invoking LLM with response type: %s", response_type)
        return self.__invoke_with_retry(prompt, prompt_inputs, response_type)

    def _extract_usage_metadata(self, llm_response: AIMessage):
        """
        Extracts usage metadata from the LLM response.
        """

        usage_metadata = llm_response.usage_metadata
        if usage_metadata:
            self._last_metrics = TokenUsage(
                input_tokens=usage_metadata.get('input_tokens', 0),
                output_tokens=usage_metadata.get('output_tokens', 0),
                total_tokens=usage_metadata.get('total_tokens', 0)
            )
            logger.debug("Extracted usage metadata: %s", self._last_metrics)
        else:
            self._last_metrics = TokenUsage()

        return llm_response

    def _parse_llm_response(
        self,
        runnable_response: Any,
        response_type: Literal['string', 'json', 'raw'],
        response_model: Type[TResponse] = None
    ) -> Union[str, dict, AIMessage, TResponse, AdditionalInfoRequest]:
        """
        Parses the output from the LLM invocation.

        For response_type 'raw', if the runnable_response has a 'content' attribute, that is used.
        For 'string' and 'json', the method attempts to parse the output as JSON if possible.
        If a response_model is provided, it first attempts to parse the output using that model;
        if that fails due to a validation error, it then attempts to parse the output as an AdditionalInfoRequest.
        If no response_model is provided, it checks if the parsed output is a dict with a "question" key
        and, if so, attempts to parse it as an AdditionalInfoRequest.

        Returns:
            The final parsed response.
        """
        # For raw responses, try to retrieve content
        if response_type == 'raw' and hasattr(runnable_response, "content"):
            raw_output = runnable_response.content
        else:
            raw_output = runnable_response

        # Try to parse raw_output as JSON if it's a string
        if isinstance(raw_output, str):
            try:
                parsed = json.loads(raw_output)
            except (ValueError, TypeError):
                parsed = raw_output  # Fallback: use the raw string
        elif isinstance(raw_output, dict):
            parsed = raw_output
        else:
            # If not a string or dict, convert to string and try to parse JSON
            try:
                parsed = json.loads(str(raw_output))
            except Exception:
                parsed = str(raw_output)

        # If a response model is provided, attempt to parse with it.
        if response_model:
            try:
                # If parsed is a dict, unpack; else, try parsing from raw string.
                final_response = response_model(**parsed)
            except ValidationError as e:
                logger.debug("Parsing with response_model (%s) failed: %s", response_model.__name__, e)
                try:
                    final_response = AdditionalInfoRequest(**parsed)
                except ValidationError as e2:
                    raise ValueError(
                        f"Failed {response_model.__name__}: {e}. Failed AdditionalInfoRequest: {e2}"
                    )
            return final_response
        else:
            # No response model provided.
            if isinstance(parsed, dict) and "question" in parsed:
                try:
                    final_response = AdditionalInfoRequest(**parsed)
                except ValidationError as ve:
                    logger.debug("Parsing as AdditionalInfoRequest failed: %s", ve)
                    final_response = parsed
            else:
                final_response = parsed
            return final_response

    def __invoke_with_retry(
        self, 
        prompt: BasePrompt,
        prompt_inputs: Dict[str, Any],
        response_type: Literal['string', 'json', 'raw'] = 'raw',
        response_model: Type[TResponse] = None
    ) -> LLMOutput[Union[str, dict, AIMessage, TResponse, AdditionalInfoRequest]]:
        """
        Invokes the LLM with a retry mechanism.

        If a response_model is provided, this method first attempts to parse the LLM's output using that model.
        If parsing fails due to validation errors, it then attempts to parse the output as an AdditionalInfoRequest.
        If no response_model is provided, it still checks if the output can be interpreted as an AdditionalInfoRequest
        (for example, if the output is a JSON dict with a "question" key).

        Returns:
            LLMOutput containing either the final response (of type TResponse) or an AdditionalInfoRequest.
        """
        attempt = 0
        rendered_prompt = prompt.render(**prompt_inputs)
        final_prompt = PromptTemplate.from_template(rendered_prompt)
        feedback = ""
        
        current_metrics = MetricsContext(self.provider, self.model)
        self._callbacks = [LLMMetricsCallback(current_metrics)]

        while attempt < self._max_retries:
            try:
                logger.debug("Attempting to invoke LLM (attempt %d).", attempt + 1)
                runnable = self._create_chain(final_prompt, response_type)
                runnable_response = runnable.invoke(
                    {'feedback': feedback},
                    config={"callbacks": self._callbacks}
                )

                final_response = self._parse_llm_response(runnable_response, response_type, response_model)
            
                # Reset retry backoff to default after successful invocation
                self._current_retry_backoff = self._retry_backoff
                logger.info("LLM invocation successful on attempt %d.", attempt + 1)
                current_metrics.save_to_db()
                return LLMOutput(final_response, self._last_metrics)
            except KeyError as ke:
                logger.error("Unrecoverable KeyError in prompt formatting: %s", ke, exc_info=True)
                raise RuntimeError(f"Unrecoverable error in prompt template: {ke}") from ke 
            except Exception as e:
                attempt += 1
                logger.warning(
                    "Invocation failed (attempt %d/%d): %s", attempt, self._max_retries, str(e)
                )
                feedback = str(e)
                if attempt >= self._max_retries:
                    logger.error(
                        "LLM invocation failed after %d attempts. Error: %s", self._max_retries, str(e)
                    )
                    self._current_retry_backoff = self._retry_backoff
                    raise RuntimeError(f"LLM invocation failed: {e}")
                sleep(self._current_retry_backoff)
                logger.debug("Retrying after backoff: %.2f seconds.", self._current_retry_backoff)
                self._current_retry_backoff *= 2
