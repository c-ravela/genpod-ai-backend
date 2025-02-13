from agents.rag._internal.rag_graph import RAGGraph
from agents.rag._internal.rag_work_flow import RAGWorkFlow
from core.agent import BaseAgent
from llms import LLM
from utils.logs.logging_utils import logger


class RAGAgent(BaseAgent[RAGGraph]):
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
        collection_name: str,
        persist_directory: str,
        recursion_limit: int,
        persistance_db_path: str,
    ):
        """
        Initialize the RAGAgent with the required workflow and graph components.

        Args:
            id (str): Unique identifier for the agent.
            name (str): The name of the agent.
            description (str): Brief description of the agent's functionality.
            llm (LLM): The language model used for generation and grading.
            collection_name (str): Name of the vector store collection.
            persist_directory (str): Directory where the vector store is persisted.
            recursion_limit (int): Maximum recursion depth for state transitions in the graph.
            persistance_db_path (str): Path to the persistence database for saving graph state.
        """
        logger.info(
            "Initializing RAGAgent | ID: %s | Name: %s | Collection: %s | Persist Dir: %s | Recursion Limit: %d | Persistence DB: %s",
            id, name, collection_name, persist_directory, recursion_limit, persistance_db_path
        )

        work_flow = RAGWorkFlow(id, name, llm, collection_name, persist_directory)
        logger.debug("RAGWorkFlow initialized for agent: %s", name)

        rag_graph = RAGGraph(work_flow, recursion_limit, persistance_db_path)
        logger.debug(
            "RAGGraph created for agent: %s with recursion_limit=%d and persistence_db_path=%s",
            name, recursion_limit, persistance_db_path
        )

        super().__init__(id, name, description, llm, rag_graph)
        logger.info("RAGAgent successfully initialized | ID: %s | Name: %s", id, name)
