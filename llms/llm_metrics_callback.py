from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Dict, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from apis.microservice_llm_metrics.controller import \
    MicroserviceLLMMetricsController
from context.context import GenpodContext
from database.entities.microservice_llm_metrics import MicroserviceLLMMetrics
from utils.logs.logging_utils import logger


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class TimeRecord:
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        if self.start_time is None or self.end_time is None:
            logger.error("Cannot calculate duration: Missing start or end time.")
            return None

        duration = self.end_time - self.start_time
        logger.debug(f"Calculated duration(seconds): {duration}")
        return duration


@dataclass
class MetricsContext:
    model_provider: str
    model_name: str

    total_time_record: Dict[UUID, TimeRecord] = field(init=False, default_factory=dict)
    llm_time_records: Dict[UUID, TimeRecord] = field(init=False, default_factory=dict)
    prompt_time_records: Dict[UUID, TimeRecord] = field(init=False, default_factory=dict)
    token_usage: TokenUsage = field(init=False, default_factory=TokenUsage)

    _total_duration: float = field(init=False, default=0)
    _total_llm_duration: float = field(init=False, default=0)

    _total_prompt_duration: float = field(init=False, default=0)
    _prompt_eval_rate: float = field(init=False, default=0)

    _eval_duration: float = field(init=False, default=0)
    _eval_rate: float = field(init=False, default=0)

    _genpod_context: GenpodContext = field(init=False, repr=False, default=GenpodContext())

    def _finalize_metrics(self) -> None:
        """Compute and log final metrics."""
        logger.debug("Finalizing metrics calculations.")

        for id, time_record in self.llm_time_records.items():
            duration = time_record.duration
            if duration is not None:
                self._total_llm_duration += duration
            else:
                logger.warning(f"Duration not available for LLM run_id: {id}")
        
        for id, time_record in self.prompt_time_records.items():
            duration = time_record.duration
            if duration is not None:
                self._total_prompt_duration += duration
            else:
                logger.warning(f"Duration not available for Prompt run_id: {id}")

        for id, time_record in self.total_time_record.items():
            duration = time_record.duration
            if duration is not None:
                self._total_duration = duration
                break
            else:
                logger.error(f"Failed to calculate total duration for run_id: {id}")
        
        if self._total_prompt_duration > 0:
            self._prompt_eval_rate = self.token_usage.input_tokens / self._total_prompt_duration
            logger.debug(f"Prompt evaluation rate calculated: {self._prompt_eval_rate}")
        else:
            self._prompt_eval_rate = 0
            logger.warning("Total prompt duration is zero; cannot compute prompt_eval_rate.")
        
        self._eval_duration = self._total_prompt_duration + self._total_llm_duration
        if self._eval_duration > 0:
            self._eval_rate = self.token_usage.total_tokens / self._eval_duration
            logger.debug(f"Evaluation duration: {self._eval_duration}, rate: {self._eval_rate}")
        else:
            self._eval_rate = 0
            logger.warning("Total eval duration is zero; cannot compute eval_rate.")

    def save_to_db(self) -> None:
        logger.info("Saving metrics to the database.")
        self._finalize_metrics()
        current_metrics = MicroserviceLLMMetrics(
            project_id=self._genpod_context.project_id,
            microservice_id=self._genpod_context.microservice_id,
            agent_id=self._genpod_context.current_agent.agent_id,
            provider=self.model_provider,
            model=self.model_name,
            input_tokens=self.token_usage.input_tokens,
            output_tokens=self.token_usage.output_tokens,
            total_tokens=self.token_usage.total_tokens,
            llm_duration=self._total_llm_duration,
            prompt_duration=self._total_prompt_duration,
            prompt_eval_rate=self._prompt_eval_rate,
            eval_duration=self._eval_duration,
            eval_rate=self._eval_rate,
            total_llm_processing_duration=self._total_duration,
            created_by=self._genpod_context.user_id,
            updated_by=self._genpod_context.user_id
        )

        metrics_controller = MicroserviceLLMMetricsController()
        try:
            metrics_controller.create(current_metrics)
            logger.info("Metrics saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save metrics to the database: {e}")


class LLMMetricsCallback(BaseCallbackHandler):
    def __init__(self, context: MetricsContext):
        super().__init__()
        self.context = context
        logger.debug(f"LLMMetricsCallback initialized with context: {context}")

    def _llm_start(self, run_id: UUID) -> None:
        """Handle LLM start event."""
        logger.info(f"LLM start event received for run_id: {run_id}.")
        if self.context.llm_time_records:
            logger.warning(f"New LLM start received with run_id: {run_id} while another run_id is active")

        self.context.llm_time_records[run_id] = TimeRecord(start_time=perf_counter())

    def _llm_end(self, run_id: UUID, response: LLMResult) -> None:
        """Handle LLM end event."""
        if run_id not in self.context.llm_time_records:
            logger.error(f"LLM end received without a start for run_id: {run_id}")
            return

        self.context.llm_time_records[run_id].end_time = perf_counter()
        logger.info(f"LLM end event processed for run_id: {run_id}.")

        for generations in response.generations:
            for generation in generations:
                usage_metadata = generation.message.usage_metadata
                if usage_metadata:
                    self.context.token_usage.input_tokens += usage_metadata.get("input_tokens", 0)
                    self.context.token_usage.output_tokens += usage_metadata.get("output_tokens", 0)
                    self.context.token_usage.total_tokens += usage_metadata.get("total_tokens", 0)
                    logger.debug(f"Updated token usage: {self.context.token_usage}")

    def _prompt_start(self, run_id: UUID, run_type: str) -> None:
        """Handle prompt (chain) start event."""
        logger.info(f"Prompt start event received for run_id: {run_id}, type: {run_type}.")

        if len(self.context.total_time_record) == 0 and len(self.context.prompt_time_records) == 0:
            self.context.total_time_record[run_id] = TimeRecord(start_time=perf_counter())
            logger.debug(f"Captured total start time for run_id: {run_id}.")

        if not run_type or run_type != "prompt":
            logger.warning(f"Invalid prompt type `{run_type}` for run_id: {run_id}.")
            return
        
        self.context.prompt_time_records[run_id] = TimeRecord(start_time=perf_counter())
        logger.debug(f"Prompt start time recorded for run_id: {run_id}.")

    def _prompt_end(self, run_id: UUID) -> None:
        """Handle prompt (chain) end event."""
        logger.info(f"Prompt end event received for run_id: {run_id}.")

        if run_id in self.context.total_time_record:
            self.context.total_time_record[run_id].end_time = perf_counter()
            logger.debug(f"Total end time recorded for run_id: {run_id}.")

        if run_id not in self.context.prompt_time_records:
            logger.warning(f"Prompt end received without a start for run_id: {run_id}")
            return

        self.context.prompt_time_records[run_id].end_time = perf_counter()
        logger.info(f"Prompt end time recorded for run_id: {run_id}.")

    def on_chat_model_start(self, serialized: Dict[str, Any], messages: any, **kwargs) -> None:
        """Handle chat model start event."""
        logger.debug(f"Chat model start event: serialized={serialized}, messages={messages}, kwargs={kwargs}")
        self._llm_start(kwargs["run_id"])

    def on_llm_start(self, serialized, prompts, *, run_id, parent_run_id = None, tags = None, metadata = None, **kwargs) -> None:
        """Handle LLM start event."""
        logger.debug(f"LLM start event: serialized={serialized}, kwargs={kwargs}")
        self._llm_start(run_id)

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """Handle LLM end event."""
        logger.debug(f"LLM end event: response={response}, kwargs={kwargs}")
        self._llm_end(kwargs["run_id"], response)

    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id = None, tags = None, metadata = None, **kwargs):
        """Handle chain start event."""
        logger.debug(f"Chain start event: serialized={serialized}, inputs={inputs}, kwargs={kwargs}")
        self._prompt_start(run_id, kwargs.get("run_type", None))

    def on_chain_end(self, outputs, *, run_id, parent_run_id = None, **kwargs):
        """Handle chain end event."""
        logger.debug(f"Chain end event: outputs={outputs}, run_id={run_id}, kwargs={kwargs}")
        self._prompt_end(run_id)
