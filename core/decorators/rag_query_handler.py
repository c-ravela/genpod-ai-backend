from functools import wraps
from typing import Any, Dict

from pydantic import BaseModel, Field

from context import GenpodContext
from llms import LLMOutput
from models import (AdditionalInfoRequest, PStatus, RagResponseType, Status,
                    Task)
from utils.logs.logging_utils import logger

FAQ_KEY = 'faq'
MAX_FALLBACK_ATTEMPTS = 10
DEFAULT_FALLBACK_MESSAGE = (
    "Fallback Message: Additional details could not be retrieved at this time. "
    "Please proceed with the task using the available information without asking for further clarification."
)


class TaskRecord(BaseModel):
    """
    Tracks the FAQ and banned status for a specific task.
    """
    id: str = Field(default="")
    banned: bool = Field(default=False)
    faq: Dict[str, str] = Field(default_factory=dict)


class AgentRecord(BaseModel):
    """
    Tracks all tasks for a given agent.
    """
    id: str = Field(default="")
    tasks: Dict[str, TaskRecord] = Field(default_factory=dict)


class FAQHistory(BaseModel):
    """
    Central registry of FAQ history across all agents.
    """
    agents: Dict[str, AgentRecord] = Field(default_factory=dict)

faq_history: FAQHistory = FAQHistory()

def _build_faq_string(task: TaskRecord) -> str:
    """
    Builds a formatted FAQ string from the provided task record.
    
    Each Q&A pair is numbered, e.g.:
        1. Question: <question>
           Answer: <answer>
    
    Args:
        task (TaskRecord): The record containing FAQ pairs.
    
    Returns:
        str: A formatted string representing the FAQ, or an empty string if no entries exist.
    """
    faq_str = ""
    for idx, (question, answer) in enumerate(task.faq.items(), 1):
        faq_str += f"{idx}. Question: {question}\n   Answer: {answer}\n"
    return faq_str

def rag_query_handler(method):
    """
    Decorator for integrating the RAG (Retrieval-Augmented Generation) middleware into LLM invocations.
    
    This decorator expects the decorated method to have a signature similar to:
    
        def invoke(self, prompt: BasePrompt, prompt_inputs: Dict[str, Any],
                   response_type: str = 'raw') -> LLMOutput[...]:
            ...

    Behavior:
      - For a RagInstructionsPrompt, it:
          1. Retrieves or initializes the FAQ tracking records for the current agent and task.
          2. If the task is banned, disables RAG by setting prompt.use_rag to False.
          3. Otherwise, if self.use_rag is enabled, injects the FAQ string into prompt_inputs.
      - The decorated method is invoked.
      - If the LLM returns an AdditionalInfoRequest, the decorator:
          1. Extracts the clarifying question.
          2. Constructs a detailed RAGMiddlewareInput (with user prompt, project status, directory, and a Task).
          3. Invokes the RAG middleware to obtain a fallback answer.
          4. Updates the FAQ record for the task with the new Q&A pair.
          5. Rebuilds the FAQ string and re-injects it into prompt_inputs.
          6. Re-invokes the LLM method.
      - This loop repeats (up to MAX_FALLBACK_ATTEMPTS) until a final answer is produced.
      - If the maximum attempts are exceeded, a RuntimeError is raised.

    Usage:
        @rag_query_handler
        def invoke(self, prompt: BasePrompt, prompt_inputs: Dict[str, Any],
                   response_type: str = 'raw') -> LLMOutput[...]:
            ...

    Returns:
        The result from the underlying LLM invocation once a valid response is obtained.
    """
    from core.prompt.base_prompt import BasePrompt
    from core.prompt.rag_instructions_prompt import RagInstructionsPrompt

    @wraps(method)
    def wrapper(self, prompt: BasePrompt, prompt_inputs: Dict[str, Any], *args, **kwargs):

        from agents.rag_middleware import (RAGMiddleware, RAGMiddlewareInput,
                                           RAGMiddlewareOutput)
        genpod_context: GenpodContext = GenpodContext.get_context()
        global faq_history

        if isinstance(prompt, RagInstructionsPrompt):
            logger.debug("rag_query_handler: Detected RagInstructionsPrompt; processing RAG-specific logic.")
            current_task_id = genpod_context.current_task.task_id
            agent_id = self.agent_id

            agent_record = faq_history.agents.get(agent_id) or AgentRecord(id=agent_id)
            task_record = agent_record.tasks.get(current_task_id) or TaskRecord(id=current_task_id)
            agent_record.tasks[current_task_id] = task_record
            faq_history.agents[agent_id] = agent_record

            if task_record.banned:
                logger.info("rag_query_handler: Agent '%s' is banned for task '%s'. Disabling RAG for this query.",
                            agent_id, current_task_id)
                prompt.use_rag = False
            else:
                if self.use_rag:
                    faq_str = _build_faq_string(task_record)
                    prompt_inputs[FAQ_KEY] = faq_str
                    logger.debug("rag_query_handler: Injected FAQ context into prompt_inputs:\n%s", faq_str)

        fallback_attempts = 0
        while fallback_attempts < MAX_FALLBACK_ATTEMPTS:
            logger.debug("rag_query_handler: Invocation attempt %d.", fallback_attempts + 1)
            result: LLMOutput = method(self, prompt, prompt_inputs, *args, **kwargs)

            if isinstance(result.response, AdditionalInfoRequest):
                additional_info = result.response
                clarifying_question = additional_info.question
                logger.info("rag_query_handler: Received AdditionalInfoRequest with clarifying question: '%s'", clarifying_question)

                current_task_id = genpod_context.current_task.task_id
                rag_middleware_task = Task(
                    task_status=Status.NEW,
                    description="Process the clarifying query by retrieving relevant context and synthesizing a comprehensive, context-aware answer."
                )
                rag_input = RAGMiddlewareInput(
                    user_prompt=genpod_context.user_prompt,
                    project_status=PStatus.MONITORING,
                    project_directory=genpod_context.project_path,
                    current_task=rag_middleware_task,
                    agent_id=self.agent_id,
                    task_id=current_task_id,
                    query=clarifying_question
                )
                logger.debug("rag_query_handler: Invoking RAG middleware with input: %s", rag_input)
                rag_output_raw = RAGMiddleware.get_instance().invoke(rag_input)
                rag_output = RAGMiddlewareOutput(**rag_output_raw)
                rag_middleware_task = rag_output.current_task

                if rag_middleware_task.task_status == Status.DONE:
                    if rag_output.response_type == RagResponseType.ANSWERED:
                        logger.debug("rag_query_handler: Fallback query answered successfully.")
                        fallback_answer = rag_output.response
                    else:
                        if rag_output.response_type == RagResponseType.REJECTED:
                            logger.warning("rag_query_handler: Fallback query rejected. Marking task as banned.")
                            task_record.banned = True
                            fallback_answer = DEFAULT_FALLBACK_MESSAGE
                            task_record.faq[clarifying_question] = fallback_answer
                            # Disable RAG access
                            prompt.use_rag = False
                            # Increment fallback_attempts so that we eventually exit the loop
                            fallback_attempts += 1
                            logger.debug("rag_query_handler: RAG access disabled; re-invoking LLM for a final attempt without RAG.")
                            continue
                        else:
                            logger.warning("rag_query_handler: Fallback query not answered. Using default fallback message.")
                            fallback_answer = DEFAULT_FALLBACK_MESSAGE
                else:
                    logger.warning("rag_query_handler: RAG middleware returned an unknown task status. Using default fallback message.")
                    fallback_answer = DEFAULT_FALLBACK_MESSAGE

                task_record.faq[clarifying_question] = fallback_answer
                logger.debug("rag_query_handler: Updated FAQ for task '%s': %s", current_task_id, task_record.faq)

                if self.use_rag and not task_record.banned:
                    faq_str = _build_faq_string(task_record)
                    prompt_inputs[FAQ_KEY] = faq_str
                    logger.debug("rag_query_handler: Re-injected updated FAQ context into prompt_inputs:\n%s", faq_str)

                fallback_attempts += 1
                logger.debug("rag_query_handler: Re-invoking method with updated FAQ context (fallback attempt %d).", fallback_attempts)
                continue
            else:
                logger.debug("rag_query_handler: LLM response accepted; ending fallback loop.")
                return result
        
        error_message = (
            f"Maximum fallback attempts ({MAX_FALLBACK_ATTEMPTS}) reached; "
            f"unable to obtain a final response after {fallback_attempts} attempts."
        )
        logger.error("rag_query_handler: %s", error_message)
        raise RuntimeError(error_message)

    return wrapper
