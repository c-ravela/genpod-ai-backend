from agents.llama_index_vector_rag._internal.llama_index_vector_rag_graph import LlamaIndexVectorRAGGraph
from agents.llama_index_vector_rag._internal.llama_index_vector_rag_workflow import LlamaIndexVectorRAGWorkFlow

from core.agent import BaseAgent
from llms import LLM
from utils.logger import logger


class LlamaIndexVectorRAGAgent(BaseAgent[LlamaIndexVectorRAGGraph]):
    """
    Retrieval-Augmented Generation (RAG) Agent.

    This agent implements a RAG workflow that processes queries by retrieving relevant documents,
    generating responses, and grading the outputs. It integrates a workflow graph (RAGGraph) with
    a language model (LLM) to manage state transitions and response generation.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        llm: LLM,
        recursion_limit: int,
        persistence_db_path: str,
        config_path: str
    ):
        """
        Initialize the RAGAgent with the required workflow and graph components.

        Args:
            id (str): Unique identifier for the agent.
            name (str): The name of the agent.
            description (str): Brief description of the agent's functionality.
            llm (LLM): The language model used for generation and grading.
            recursion_limit (int): Maximum recursion depth for state transitions in the graph.
            persistence_db_path (str): Path to the persistence database for saving graph state.
        """
        logger.info(
            "Initializing RAGAgent | ID: %s | Name: %s | Recursion Limit: %d | Persistence DB: %s | Config Path: %s",
            id, name, recursion_limit, persistence_db_path, config_path
        )

        work_flow = LlamaIndexVectorRAGWorkFlow(id, name, llm, config_path)
        logger.debug("RAGWorkFlow initialized for agent: %s", name)

        rag_graph = LlamaIndexVectorRAGGraph(work_flow, recursion_limit, persistence_db_path)
        logger.debug(
            "RAGGraph created for agent: %s with recursion_limit=%d and persistence_db_path=%s",
            name, recursion_limit, persistence_db_path
        )

        super().__init__(id, name, description, llm, rag_graph)
        logger.info("RAGAgent successfully initialized | ID: %s | Name: %s", id, name)
