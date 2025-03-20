from agents.reviewer._internal.reviewer_graph import ReviewerGraph
from agents.reviewer._internal.reviewer_work_flow import ReviewerWorkFlow
from core.agent import BaseAgent
from llms import LLM
from utils.logger import logger


class ReviewerAgent(BaseAgent[ReviewerGraph]):
    """
    A ReviewerAgent orchestrates the code review process by leveraging a workflow and graph-based
    approach. It utilizes an LLM to process review prompts and manage review states throughout
    the review process.
    """
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        llm: LLM,
        recursion_limit: int,
        persistence_db_path: str,
        use_rag: bool = False
    ):
        """
        Initializes a ReviewerAgent with the provided configuration.

        This constructor sets up the review workflow and the reviewer graph, which together
        manage the review process. It then initializes the base agent with these components.

        Args:
            id (str): Unique identifier for the agent.
            name (str): Human-readable name of the agent.
            description (str): Brief description of the agent's functionality.
            llm (LLM): Instance of the language model to be used.
            recursion_limit (int): Maximum number of recursive operations allowed.
            persistence_db_path (str): File path to the persistence database.
            use_rag (bool, optional): Whether to use Retrieval-Augmented Generation. Defaults to False.
        """
        logger.info(
            "Initializing ReviewerAgent | ID: %s | Name: %s | Recursion Limit: %d | Persistence DB: %s | RAG Enabled: %s",
            id, name, recursion_limit, persistence_db_path, use_rag
        )        
        
        work_flow = ReviewerWorkFlow(id, name, llm, use_rag)
        logger.debug("ReviewerWorkFlow initialized for agent: %s", name)
        
        reviewer_graph = ReviewerGraph(work_flow, recursion_limit, persistence_db_path)
        logger.debug(
            "ReviewerGraph created for agent: %s with recursion_limit=%d and persistence_db_path=%s",
            name, recursion_limit, persistence_db_path
        )

        super().__init__(id, name, description, llm, reviewer_graph, use_rag)
        logger.info("ReviewerAgent successfully initialized | ID: %s | Name: %s", id, name)
