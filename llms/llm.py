from abc import ABC, abstractmethod
from time import sleep
from typing import Any, Dict, Generic, Literal, Type, TypeVar, Union

from langchain_core.messages import AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableSequence
from pydantic import BaseModel, ValidationError

TLLMInstance = TypeVar('TLLMInstance')
TResponse = TypeVar('TResponse', bound=BaseModel)


class LLMMetrics:
    """Class to represent metrics related to LLM invocations."""

    def __init__(self, it: int, ot: int, tt: int) -> None:
        """
        Initializes the metrics with input, output, and total token counts.

        Args:
            it (int): The number of input tokens.
            ot (int): The number of output tokens.
            tt (int): The total number of tokens (input + output).
        """
        self.input_tokens = it
        self.output_tokens = ot
        self.total_tokens = tt
   
    def __str__(self) -> str:
        return (
            f"total_tokens: {self.total_tokens}, input_tokens: {self.input_tokens}, "
            f"output_tokens: {self.output_tokens}"
        )


class LLMOutput(Generic[TResponse]):
    """Represents the output of a language model invocation, including response and metrics."""
    
    def __init__(self, response: TResponse, metrics: LLMMetrics) -> None:
        """
        Initializes the LLMOutput with the response and its associated metrics.

        Args:
            response (TResponse): The response from the LLM.
            metrics (LLMMetrics): The metrics associated with the response.
        """
        self.response: TResponse = response
        self.metrics = metrics

    def __str__(self) -> str:
        return (
            f'response: {self.response}'
            f'\nmetrics: {self.metrics}'
        )


class LLM(ABC, Generic[TLLMInstance]):
    """Abstract base class for different LLM (Large Language Model) providers."""

    def __init__(self, provider: str, model: str, model_config: Dict[str, Any], llm_class: Type[TLLMInstance], max_retries: int, retry_backoff: float) -> None:
        """
        Initializes the LLM with the given provider, model, and configuration, along with retry mechanism defaults.
        """
        self.provider = provider
        self.model = model
        self.model_config = model_config
        self._llm_instance = llm_class(model=self.model, **self.model_config)
        self.__max_retries = max_retries
        self._retry_backoff = retry_backoff
        self.__current_retry_backoff = self._retry_backoff
        self._last_metrics = LLMMetrics(0, 0, 0)
        
    def invoke_with_pydantic_model(self, prompt: PromptTemplate, prompt_inputs: Dict[str, Any], response_model: Type[TResponse]) -> LLMOutput[TResponse]:
        """
        Invoke the LLM chain and return the response, with an optional retry mechanism, and parse into a structured model.
        """
        default_response_type = 'json'
        return self.__invoke_with_retry(prompt, prompt_inputs, default_response_type, response_model)

    def invoke(self, prompt: PromptTemplate, prompt_inputs: Dict[str, Any], response_type: Literal['string', 'json', 'raw'] = 'raw') -> LLMOutput[Union[str, dict, AIMessage]]:
        """
        Invoke the LLM chain and return the response in the specified format.
        """
        return self.__invoke_with_retry(prompt, prompt_inputs, response_type)

    def _extract_usage_metadata(self, llm_response: AIMessage):
        """
        Extracts usage metadata from the LLM response.
        """

        usage_metadata = llm_response.usage_metadata
        if usage_metadata:
            self._last_metrics = LLMMetrics(
                it=usage_metadata.get('input_tokens', 0),
                ot=usage_metadata.get('output_tokens', 0),
                tt=usage_metadata.get('total_tokens', 0)
            )
        else:
            self._last_metrics = LLMMetrics(0, 0, 0)

        return llm_response

    @abstractmethod
    def _create_chain(self, prompt: PromptTemplate, response_type: Literal['string', 'json', 'raw']) -> RunnableSequence:
        """Create a runnable chain for invoking the LLM. Must be implemented by provider classes."""
        pass

    def __invoke_with_retry(self, prompt: PromptTemplate, prompt_inputs: Dict[str, Any], response_type: Literal['string', 'json', 'raw'] = 'raw', response_model: Type[TResponse] = None) -> LLMOutput[Union[str, dict, AIMessage, TResponse]]:
        """
        Invokes the LLM with a retry mechanism.
        """
        attempt = 0
        wrapped_prompt = self.__wrap_prompt_with_instructions(prompt, prompt_inputs)
        feedback = ""
        
        while attempt < self.__max_retries:
            try:
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
                self.__current_retry_backoff = self._retry_backoff
                return LLMOutput(final_response, self._last_metrics)
            
            except Exception as e:
                attempt += 1
                feedback = str(e)
                if attempt >= self.__max_retries:
                    self.__current_retry_backoff = self._retry_backoff
                    raise RuntimeError(f"LLM invocation failed after {self.__max_retries} attempts: {e}")
                else:
                    # print(f"Invocation failed (attempt {attempt}/{self.__max_retries}). Retrying in {self.__current_retry_backoff} seconds...")
                    sleep(self.__current_retry_backoff)
                    self.__current_retry_backoff *= 2

    def __wrap_prompt_with_instructions(self, prompt: PromptTemplate, prompt_inputs: Dict[str, Any]) -> PromptTemplate:
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

            `{feedback}`

            {formatted_user_prompt}
            """,
            input_variables=['feedback'],
            partial_variables={
                "formatted_user_prompt": user_prompt
            }
        )

        return wrapped_prompt
    
    def __str__(self):
        return (
            f"LLM Provider: {self.provider}\n"
            f"Model: {self.model}\n"
            f"Model Config: {self.model_config}\n"
            f"Max Retries: {self.__max_retries}\n"
            f"Retry Backoff: {self._retry_backoff}\n"
            f"Last Metrics: Input Tokens: {self._last_metrics.input_tokens}, "
            f"Output Tokens: {self._last_metrics.output_tokens}, "
            f"Total Tokens: {self._last_metrics.total_tokens}"
        )
