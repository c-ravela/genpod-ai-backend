from agents.planner._internal.planner_graph import PlannerGraph
from agents.planner._internal.planner_work_flow import PlannerWorkFlow
from core.agent import BaseAgent
from llms import LLM
from utils.logs.logging_utils import logger


class PlannerAgent(BaseAgent[PlannerGraph]):
    """
    PlannerAgent orchestrates the planning workflow by integrating the PlannerWorkFlow and PlannerGraph.

    This agent is responsible for initializing the planning workflow with the provided language model (LLM),
    recursion limit, persistence database path, and optional Retrieval-Augmented Generation (RAG) settings.
    It constructs a PlannerGraph from a PlannerWorkFlow instance and passes it to the BaseAgent for further processing.
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
        Initialize the PlannerAgent.

        Args:
            id (str): Unique identifier for the agent.
            name (str): Name of the agent.
            llm (LLM): Language model instance used by the agent.
            recursion_limit (int): The maximum recursion depth allowed for the planner graph.
            persistance_db_path (str): Path to the persistence database for storing the planner state.
            use_rag (bool, optional): Flag indicating whether to enable Retrieval-Augmented Generation (RAG). Defaults to False.
        """
        logger.debug(
            "Initializing PlannerAgent with id: %s, name: %s, recursion_limit: %d, persistance_db_path: %s, use_rag: %s",
            id, name, recursion_limit, persistance_db_path, use_rag
        )
        # Initialize the planning workflow with the provided parameters.
        work_flow = PlannerWorkFlow(id, name, llm, use_rag)
        logger.debug("Created PlannerWorkFlow for agent %s", name)
        
        planner_graph = PlannerGraph(work_flow, recursion_limit, persistance_db_path)
        logger.debug("Created PlannerGraph for agent %s", name)
        
        super().__init__(id, name, llm, planner_graph, use_rag)
        logger.info("Initialized PlannerAgent with id: %s, name: %s", id, name)
