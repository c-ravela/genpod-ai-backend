from typing import List

from agents.rag_middleware._internal.rag_middleware_work_flow import \
    RAGMiddlewareWorkFlow
from agents.rag_middleware._internal.rag_middlware_graph import \
    RAGMiddlewareGraph
from agents.rag_middleware.registry import (get_registered_agent_count,
                                            register_rag_agent)
from core.agent import BaseAgent
from llms import LLM
from utils.logs.logging_utils import logger

dummy_rag_agent = BaseAgent(
    id="_dummy_rag_agent_01_",
    name="Dummy Rag Agent",
    llm=None,
    graph=None,
)

dummy_rag_agent_description = (
    "Fallback agent: Used when no suitable RAG agent is found (e.g., when all agents have a confidence value of 0). "
    "The LLM should return this agent's ID in such cases."
)

# Register the dummy agent only if there is at least one registered RAG agent.
if get_registered_agent_count() > 0:
    logger.info("Registered RAG agents exist; registering dummy agent as fallback.")
    register_rag_agent(dummy_rag_agent, dummy_rag_agent_description)
else:
    logger.info("No RAG agents registered; dummy agent will not be added.")


class RAGMiddleware(BaseAgent[RAGMiddlewareGraph]):
    """
    RAGMiddleware integrates retrieval-augmented generation (RAG) agents into a processing workflow.

    This middleware processes incoming queries by selecting an appropriate RAG agent to generate a response.
    It leverages a language model for agent selection and manages overall process control—including error handling
    and task transitions—by coordinating with an internal workflow and processing graph.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        llm: LLM,
        recursion_limit: int,
        persistence_db_path: str,
        rag_agents: List[BaseAgent],
    ) -> None:
        """
        Initializes the RAG middleware.

        Args:
            id (str): Unique identifier for this middleware instance.
            name (str): Name of the middleware instance.
            description (str): Brief description of the middleware's functionality.
            llm (LLM): Language model used for agent selection and query processing.
            recursion_limit (int): The maximum recursion depth for the processing graph.
            persistence_db_path (str): Path to the persistence database.
            rag_agents (List[BaseAgent]): A list of available RAG agent instances.
        """
        self.rag_agents = rag_agents
        logger.info(
            "Initializing RAGMiddleware | ID: %s | Name: %s | Number of RAG Agents: %d",
            id, name, len(self.rag_agents)
        )

        # Initialize the RAG workflow with the provided parameters.
        work_flow = RAGMiddlewareWorkFlow(id, name, llm, rag_agents, dummy_rag_agent.id)
        logger.debug("RAGMiddlewareWorkFlow initialized for middleware: %s", name)

        # Construct the processing graph using the workflow and persistence settings.
        graph = RAGMiddlewareGraph(work_flow, recursion_limit, persistence_db_path)
        logger.debug(
            "RAGMiddlewareGraph created for middleware: %s with recursion_limit=%d and persistence_db_path=%s",
            name, recursion_limit, persistence_db_path
        )

        # Initialize the BaseAgent with the configured graph.
        super().__init__(id, name, description, llm, graph)
        
        logger.info("RAGMiddleware successfully initialized | ID: %s | Name: %s", id, name)
