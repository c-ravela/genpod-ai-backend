from abc import ABC, ABCMeta, abstractmethod
from time import sleep
from typing import Any, Dict, Generic, Literal, Type, TypeVar, Union

from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableSequence
from pydantic import BaseModel, ValidationError

from utils.logs.logging_utils import logger

TLLMInstance = TypeVar('TLLMInstance')
TResponse = TypeVar('TResponse', bound=BaseModel)


class LLMMetrics:
    """Class to represent metrics related to LLM invocations."""

    def __init__(self, input_tokens: int, output_tokens: int, total_tokens: int) -> None:
        """
        Initializes the metrics with input, output, and total token counts.

        Args:
            input_tokens (int): The number of input tokens.
            output_tokens (int): The number of output tokens.
            total_tokens (int): The total number of tokens (input + output).
        """
        logger.debug(
            "Initializing LLMMetrics with input_tokens: %d, output_tokens: %d, total_tokens: %d",
            input_tokens, output_tokens, total_tokens
        )
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
    
    def __repr__(self) -> str:
        representation = (
            f"<LLMMetrics(input_tokens={self.input_tokens}, "
            f"output_tokens={self.output_tokens}, "
            f"total_tokens={self.total_tokens})>"
        )
        logger.debug("Generated LLMMetrics representation: %s", representation)
        return representation

class LLMOutput(Generic[TResponse]):
    """Represents the output of a language model invocation, including response and metrics."""
    
    def __init__(self, response: TResponse, metrics: LLMMetrics) -> None:
        """
        Initializes the LLMOutput with the response and its associated metrics.

        Args:
            response (TResponse): The response from the LLM.
            metrics (LLMMetrics): The metrics associated with the response.
        """
        logger.debug(
            "Creating LLMOutput with response: %s and metrics: %s", response, metrics
        )
        self.response: TResponse = response
        self.metrics = metrics

    def __repr__(self) -> str:
        representation = (
            f"<LLMOutput(response={self.response}, metrics={self.metrics})>"
        )
        logger.debug("Generated LLMOutput representation: %s", representation)
        return representation


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
        self._llm_instance = self._initialize_llm_instance()
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._current_retry_backoff = self._retry_backoff
        self._last_metrics = LLMMetrics(0, 0, 0)
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
        prompt: PromptTemplate,
        prompt_inputs: Dict[str, Any],
        response_model: Type[TResponse]
    ) -> LLMOutput[TResponse]:
        """
        Invoke the LLM chain and return the response, with an optional retry mechanism, and parse into a structured model.
        """
        logger.debug("Invoking LLM with structured model response.")
        return self.__invoke_with_retry(prompt, prompt_inputs, 'json', response_model)

    def invoke(
        self,
        prompt: PromptTemplate,
        prompt_inputs: Dict[str, Any],
        response_type: Literal['string', 'json', 'raw'] = 'raw'
    ) -> LLMOutput[Union[str, dict, AIMessage]]:
        """
        Invoke the LLM chain and return the response in the specified format.
        """
        logger.debug("Invoking LLM with response type: %s", response_type)
        return self.__invoke_with_retry(prompt, prompt_inputs, response_type)

    def _extract_usage_metadata(self, llm_response: AIMessage):
        """
        Extracts usage metadata from the LLM response.
        """

        usage_metadata = llm_response.usage_metadata
        if usage_metadata:
            self._last_metrics = LLMMetrics(
                input_tokens=usage_metadata.get('input_tokens', 0),
                output_tokens=usage_metadata.get('output_tokens', 0),
                total_tokens=usage_metadata.get('total_tokens', 0)
            )
            logger.debug("Extracted usage metadata: %s", self._last_metrics)
        else:
            self._last_metrics = LLMMetrics(0, 0, 0)

        return llm_response

    def __invoke_with_retry(
        self, 
        prompt: PromptTemplate,
        prompt_inputs: Dict[str, Any],
        response_type: Literal['string', 'json', 'raw'] = 'raw',
        response_model: Type[TResponse] = None
    ) -> LLMOutput[Union[str, dict, AIMessage, TResponse]]:
        """
        Invokes the LLM with a retry mechanism.
        """
        attempt = 0
        wrapped_prompt = self.__wrap_prompt_with_instructions(prompt, prompt_inputs)
        feedback = ""
        
        while attempt < self._max_retries:
            try:
                logger.debug("Attempting to invoke LLM (attempt %d).", attempt + 1)
                runnable = self._create_chain(wrapped_prompt, response_type)
                runnable_response = runnable.invoke({'feedback': feedback})

                if response_model:
                    try:
                        final_response = response_model(**runnable_response)
                    except ValidationError as e:
                        raise ValueError(f"Response does not match the expected model: {e}")
                else:
                    final_response = runnable_response

                # Reset retry backoff to default after successful invocation
                self._current_retry_backoff = self._retry_backoff
                logger.info("LLM invocation successful on attempt %d.", attempt + 1)
                return LLMOutput(final_response, self._last_metrics)
            
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
                self._current_retry_backoff *= 2

    def __wrap_prompt_with_instructions(
        self,
        prompt: PromptTemplate,
        prompt_inputs: Dict[str, Any]
    ) -> PromptTemplate:
        """
        Wraps the user prompt with additional instructions and feedback handling.
        """
        user_prompt = prompt.format(**prompt_inputs)
        user_prompt = user_prompt.replace("{", "{{").replace("}", "}}")

        wrapped_prompt = PromptTemplate(
            template="""
Please adhere to the following instructions:

1. If the prompt specifies a particular format, follow it exactly.
2. Avoid including any unnecessary introductory phrases (e.g., "Here is my response") 
or tail phrases (e.g., "Thank you for your question.").

Note: If any format instructions are given and there was a previous error in your response,
you will receive feedback to improve future outputs.

`{feedback}`\n{formatted_user_prompt}
            """,
            input_variables=['feedback'],
            partial_variables={"formatted_user_prompt": user_prompt}
        )
        logger.debug("Wrapped prompt created.")
        return wrapped_prompt
    
    def __repr__(self):
        representation = (
            f"<LLM(provider={self.provider}, model={self.model}, "
            f"model_config={self.model_config}, last_metrics={self._last_metrics})>"
        )
        logger.debug("Generated LLM representation: %s", representation)
        return representation
