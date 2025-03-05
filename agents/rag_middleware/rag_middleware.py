from agents.rag_middleware._internal.rag_middleware_graph import \
    RAGMiddlewareGraph
from agents.rag_middleware._internal.rag_middleware_work_flow import \
    RAGMiddlewareWorkFlow
from agents.rag_middleware.registry import (get_rag_agents,
                                            get_registered_agent_count,
                                            register_rag_agent)
from core.agent import BaseAgent
from core.decorators import Singleton, singleton
from llms import LLM
from utils.logs.logging_utils import logger

dummy_rag_agent_description = (
    "Fallback agent: Used when no suitable RAG agent is found (e.g., when all agents have a confidence value of 0). "
    "The LLM should return this agent's ID in such cases."
)

dummy_rag_agent = BaseAgent(
    id="_dummy_rag_agent_01_",
    name="Dummy Rag Agent",
    description=dummy_rag_agent_description,
    llm=None,
    graph=None,
)

def register_dummy_agent_if_needed():
    if get_registered_agent_count() > 0:
        logger.info("Registered RAG agents exist; registering dummy agent as fallback.")
        register_rag_agent(dummy_rag_agent, dummy_rag_agent_description)
    else:
        logger.info("No RAG agents registered; dummy agent will not be added.")

@singleton
class RAGMiddleware(BaseAgent[RAGMiddlewareGraph], Singleton):
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
        research_agent: BaseAgent,
        recursion_limit: int,
        persistence_db_path: str,
        use_research_agent: bool = False
    ) -> None:
        """
        Initializes the RAG middleware.

        Args:
            id (str): Unique identifier for this middleware instance.
            name (str): Name of the middleware instance.
            description (str): Brief description of the middleware's functionality.
            llm (LLM): Language model used for agent selection and query processing.
            research_agent (BaseAgent): The agent to perform fallback research when no RAG agent is suitable.
            recursion_limit (int): The maximum recursion depth for the processing graph.
            persistence_db_path (str): Path to the persistence database.
            use_research_agent (bool): Flag indicating whether the research agent should be invoked.
        """
        register_dummy_agent_if_needed()
        rag_agents = get_rag_agents()

        logger.info(
            "Initializing RAGMiddleware | ID: %s | Name: %s | Number of RAG Agents: %d | Research Agent: %s | Use Research Agent: %s",
            id, name, len(rag_agents), research_agent.name, use_research_agent
        )


        # Initialize the RAG workflow with the provided parameters.
        work_flow = RAGMiddlewareWorkFlow(
            id,
            name,
            llm,
            rag_agents,
            dummy_rag_agent.id,
            research_agent,
            use_research_agent
        )
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
