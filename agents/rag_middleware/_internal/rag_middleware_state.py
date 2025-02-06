from typing import Any, Dict, Optional, Tuple

from pydantic import Field

from agents.rag_middleware.registry import RagAgentEntry
from core.state import *
from models import RagAgentDetail, RagResponseType
from utils import FuzzyRAGCache


class RAGMiddlewareInput(BaseInputState):
    """
    Input state for RAG middleware.

    Attributes:
        agent_id (str): ID of the agent who raised the query.
        task_id (str): ID of the task on which the agent is currently working.
        query (str): The query that the RAG middleware must address.
    """
    agent_id: str = Field(
        description="ID of the agent who raised the query."
    )
    task_id: str = Field(
        description="ID of the task on which the agent is currently working."
    )
    query: str = Field(
        description="The query that the RAG middleware must address."
    )


class RAGMiddlewareOutput(BaseOutputState):
    """
    Output state for RAG middleware.

    Attributes:
        response_type (RagResponseType): Indicates how the query was addressed (e.g., 'rag_answered',
            'no_rag_to_answer', 'rag_cache', 'rejected').
        response (str): The response generated for the query.
        selected_rag_agent (Optional[RagAgentEntry]): The RAG agent entry selected to answer the query.
            This field is populated after the agent selection process.
        selection_details (Dict[str, RagAgentDetail]): Additional details from the agent selection process, such as
            confidence scores or reasoning.
    """
    response_type: RagResponseType = Field(
        description=(
            "Indicates how the query was addressed (e.g., 'rag_answered', 'no_rag_to_answer', "
            "'rag_cache', 'rejected')."
        )
    )
    response: str = Field(
        description="The response generated for the query."
    )
    selection_details: Dict[str, RagAgentDetail] = Field(
        description="Additional details from the agent selection process, such as confidence scores or reasoning."
    )


class RAGMiddlewareState(BaseState):
    """
    State for RAG middleware.

    This unified state model is used by the RAG middleware to track input parameters, outputs, and
    internal processing data. It includes both the user-provided input as well as outputs from the RAG
    agent, along with internal fields for caching and error management.

    Attributes:
        agent_id (str): ID of the agent who raised the query.
        task_id (str): ID of the task on which the agent is currently working.
        query (str): The query that the RAG middleware must address.
        response_type (RagResponseType): How the query was addressed.
        response (str): The response generated for the query.
        selected_rag_agent (RagAgentEntry): The RAG agent entry selected to answer the query.
        selection_details (Optional[Dict[str, RagAgentDetail]]): Details from the agent selection process.
        in_memory_query_lookup (FuzzyRAGCache): In-memory lookup that holds query-response pairs.
        error_registry (Dict[Tuple[str, str], int]): Error counts for each (agent_id, task_id) pair.
        agent_last_task (Dict[str, str]): Tracks the most recent task for each agent.
        rag_agent_output (Any): Raw output from the invoked RAG agent.
    """
    agent_id: str = Field(
        default="",
        description="ID of the agent who raised the query."
    )
    task_id: str = Field(
        default="",
        description="ID of the task on which the agent is currently working."
    )
    query: str = Field(
        default="",
        description="The query that the RAG middleware must address."
    )
    response_type: RagResponseType = Field(
        default=RagResponseType.NOT_ADDRESSED,
        description=(
            "Indicates how the query was addressed (e.g., 'rag_answered', 'no_rag_to_answer', "
            "'rag_cache', 'rejected', 'not_addressed')."
        )
    )
    response: str = Field(
        default="",
        description="The response generated for the query."
    )
    selected_rag_agent: RagAgentEntry = Field(
        default_factory=dict,
        description=(
            "The RAG agent entry selected to answer the query. Populated after the agent selection process."
        )
    )
    selection_details: Dict[str, RagAgentDetail] = Field(
        default_factory=dict,
        description="Mapping of agent name to selection details."
    )

    # Internal fields for middleware processing.
    in_memory_query_lookup: FuzzyRAGCache = Field(
        default_factory=FuzzyRAGCache,
        description="In-memory lookup that holds query-response pairs for fast retrieval."
    )
    error_registry: Dict[Tuple[str, str], int] = Field(
        default_factory=dict,
        description="Error count for each (agent_id, task_id) pair."
    )
    agent_last_task: Dict[str, str] = Field(
        default_factory=dict,
        description="Tracks the most recent task for each agent."
    )
    rag_agent_output: Any = Field(
        default_factory=dict,
        description="Raw output received from the invoked RAG agent."
    )
