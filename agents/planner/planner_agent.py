from agents.planner._internal.planner_graph import PlannerGraph
from agents.planner._internal.planner_work_flow import PlannerWorkFlow
from core.agent import BaseAgent
from llms import LLM
from utils.logger import logger


class PlannerAgent(BaseAgent[PlannerGraph]):
    """
    PlannerAgent orchestrates the planning workflow by integrating PlannerWorkFlow and PlannerGraph.

    This agent is responsible for initializing the planning workflow with a provided language model (LLM),
    defining recursion limits, setting up a persistence database, and optionally enabling Retrieval-Augmented Generation (RAG).
    It constructs a PlannerGraph from a PlannerWorkFlow instance and passes it to the BaseAgent for execution.
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
        Initialize the PlannerAgent.

        Args:
            id (str): Unique identifier for the agent.
            name (str): Name of the agent.
            description (str): Brief description of the agent's functionality.
            llm (LLM): Language model instance utilized by the agent.
            recursion_limit (int): Maximum depth for recursive planning operations.
            persistence_db_path (str): File path for the persistence database storing planner state.
            use_rag (bool, optional): Enables Retrieval-Augmented Generation (RAG) if set to True. Defaults to False.
        """
        logger.info(
            "Initializing PlannerAgent | ID: %s | Name: %s | Recursion Limit: %d | Persistence DB: %s | RAG Enabled: %s",
            id, name, recursion_limit, persistence_db_path, use_rag
        )
        
        work_flow = PlannerWorkFlow(id, name, llm, use_rag)
        logger.debug("PlannerWorkFlow created for agent: %s", name)
        
        planner_graph = PlannerGraph(work_flow, recursion_limit, persistence_db_path)
        logger.debug("PlannerGraph initialized for agent: %s", name)
        
        super().__init__(id, name, description, llm, planner_graph, use_rag)
        
        logger.info("PlannerAgent successfully initialized | ID: %s | Name: %s", id, name)
