from llama_ragkit.postprocessing.postprocessor import PostProcessor

from agents.llama_index_vector_rag._internal.llama_index_vector_rag_modes import (
    LlamaRAGMode, LlamaRAGStage)
from agents.llama_index_vector_rag._internal.llama_index_vector_rag_nodes import \
    LlamaRAGNode
from agents.llama_index_vector_rag._internal.llama_index_vector_rag_prompt import \
    LlamaIndexVectorRAGPrompts
from agents.llama_index_vector_rag._internal.llama_index_vector_rag_state import (
    LlamaIndexVectorOutput, LlamaIndexVectorState)
from apis.rag_analytics.controller import RAGAnalyticsController
from context.context import GenpodContext
from core.decorators import (handle_errors_and_reset, record_node,
                             route_on_errors)
from core.workflow import BaseWorkFlow
from database.entities.rag_analytics import RAGAnalytics
from llms.llm import LLM
from models import Status
from utils.logger import logger


class LlamaIndexVectorRAGWorkFlow(BaseWorkFlow[LlamaIndexVectorRAGPrompts]):
    """
    Simplified RAG workflow over Llama-Index + Chroma that just does:
      ENTRY → EXECUTE_QUERY → EXIT
    without any grading or retry logic.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        llm: LLM,
        config_path: str
    ):
        super().__init__(
            agent_id,
            agent_name,
            LlamaIndexVectorRAGPrompts(),
            llm
        )

        # analytics context
        self._genpod_context = GenpodContext.get_context()
        self._post_processor = PostProcessor(config_path=config_path)

    @route_on_errors
    def router(self, state: LlamaIndexVectorState) -> str:
        """
        Only two active stages: EXECUTE_QUERY → EXIT
        """
        mapping = {
            LlamaRAGStage.EXECUTE_QUERY: LlamaRAGNode.EXECUTE_QUERY,
            LlamaRAGStage.COMPLETED:     LlamaRAGNode.EXIT,
        }
        next_node = mapping.get(state.current_mode_stage, LlamaRAGNode.EXIT)
        if next_node == LlamaRAGNode.EXIT and state.current_mode_stage not in mapping:
            logger.warning(
                "Agent '%s': Unrecognized mode stage '%s', defaulting to EXIT.",
                self.agent_name, state.current_mode_stage
            )

        return next_node

    @record_node(LlamaRAGNode.ENTRY)
    def entry_node(self, state: LlamaIndexVectorState) -> LlamaIndexVectorState:
        """
        Entry node: initialize workflow for a single execute_query pass.
        """
        state.operational_mode = LlamaRAGMode.EXECUTE_QUERY
        state.current_mode_stage = LlamaRAGStage.EXECUTE_QUERY
        logger.info(
            "Agent '%s': Initialized single-pass RAG workflow for query: '%s'",
            self.agent_name, state.query
        )
        return state

    @record_node(LlamaRAGNode.EXECUTE_QUERY)
    @handle_errors_and_reset
    def execute_query_node(self, state: LlamaIndexVectorState) -> LlamaIndexVectorState:
        """
        Execute the combined retrieval + generation via PostProcessor.
        """
        print("I am here")
        logger.info(
            "Agent '%s': Executing query against index: '%s'",
            self.agent_name, state.query
        )
        try:
            result = self._post_processor.query_index(state.query)
        except Exception as e:
            print(e)

        if not result:
            state.response = ""
            logger.warning(
                "Agent '%s': No result returned for query '%s'",
                self.agent_name, state.query
            )
        else:
            state.response = result["response"]
            logger.debug(
                "Agent '%s': Retrieved %d source nodes",
                self.agent_name, 0
            )

        # move to completion
        state.current_mode_stage = LlamaRAGStage.COMPLETED
        return state

    @record_node(LlamaRAGNode.EXIT)
    def exit_node(self, state: LlamaIndexVectorState) -> LlamaIndexVectorOutput:
        """
        Exit node: save analytics, mark task done and return final output.
        """
        # TODO: Disabled becaue llama_ragkit doesnt support returning the metadata 
        # To complete the analytics record.
        # self._save_analytics(state)

        state.current_task.task_status = Status.DONE
        logger.info(
            "Agent '%s': Single-pass RAG workflow completed; task marked DONE.",
            self.agent_name
        )
        return state

    def _save_analytics(self, state: LlamaIndexVectorState) -> None:
        """
        Persist analytics records for each document used in this query.
        """
        try:
            analytics_ctrl = RAGAnalyticsController()
            agent_context = (
                self._genpod_context.previous_agent
                if self._genpod_context.previous_agent
                else self._genpod_context.current_agent
            )
            documents = []
            for doc in documents:
                doc_id = getattr(doc, 'node_id', None) or getattr(doc.metadata, 'id', '')
                doc_ver = getattr(doc, 'version', '') or getattr(doc.metadata, 'version', '')

                record = RAGAnalytics(
                    agent_id=agent_context.agent_id,
                    project_id=self._genpod_context.project_id,
                    application_id=self._genpod_context.application_id,
                    session_id=agent_context.agent_session_id,
                    task_id=self._genpod_context.current_task.task_id,
                    document_id=doc_id,
                    document_version=doc_ver,
                    question=state.query,
                    raw_response=state.response,
                    size_of_data=len(state.response),
                    created_by=self._genpod_context.user_id,
                    updated_by=self._genpod_context.user_id
                )
                analytics_ctrl.create(record)
                logger.debug(
                    "Agent '%s': Saved analytics for doc '%s' version '%s'",
                    self.agent_name, doc_id, doc_ver
                )
        except Exception as e:
            logger.error(
                "Agent '%s': Failed to save analytics: %s",
                self.agent_name, e
            )
