from agents.reviewer._internal.reviewer_graph import ReviewerGraph
from agents.reviewer._internal.reviewer_work_flow import ReviewerWorkFlow
from core.agent import BaseAgent
from llms import LLM
from utils.logs.logging_utils import logger


class ReviewerAgent(BaseAgent[ReviewerGraph]):
    """
    A ReviewerAgent orchestrates the code review process by leveraging a workflow and graph-based
    approach. It utilizes an LLM to process review prompts and manage review states throughout
    the review process.

    Attributes:
        id (str): Unique identifier for the agent.
        name (str): Human-readable name of the agent.
        llm (LLM): Language model instance used for processing review tasks.
        recursion_limit (int): Maximum depth of recursive operations allowed during review.
        persistance_db_path (str): Path to the persistence database for storing review data.
        use_rag (bool): Flag indicating whether to use Retrieval-Augmented Generation.
    """
    def __init__(
        self,
        id: str,
        name: str,
        llm: LLM,
        recursion_limit: int,
        persistance_db_path: str,
        use_rag: bool = False
    ):
        """
        Initializes a ReviewerAgent with the provided configuration.

        This constructor sets up the review workflow and the reviewer graph, which together
        manage the review process. It then initializes the base agent with these components.

        Args:
            id (str): Unique identifier for the agent.
            name (str): Human-readable name of the agent.
            llm (LLM): Instance of the language model to be used.
            recursion_limit (int): Maximum number of recursive operations allowed.
            persistance_db_path (str): File path to the persistence database.
            use_rag (bool, optional): Whether to use Retrieval-Augmented Generation. Defaults to False.
        """
        logger.info(
            f"Initializing ReviewerAgent with id: {id}, name: {name}, "
            f"recursion_limit: {recursion_limit}, persistance_db_path: {persistance_db_path}, use_rag: {use_rag}"
        )        
        work_flow = ReviewerWorkFlow(id, name, llm, use_rag)
        reviewer_graph = ReviewerGraph(work_flow, recursion_limit, persistance_db_path)

        super().__init__(id, name, llm, reviewer_graph, use_rag)
        logger.info("ReviewerAgent initialized successfully.")
