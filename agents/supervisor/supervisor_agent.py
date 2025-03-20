from agents.supervisor._internal.supervisor_graph import SupervisorGraph
from agents.supervisor._internal.supervisor_work_flow import SupervisorWorkFlow
from core.agent import BaseAgent
from genpod import Team
from llms import LLM
from utils.logger import logger
from utils.otel import trace_span


class SupervisorAgent(BaseAgent[SupervisorGraph]):
    """
    Represents a supervisor agent responsible for managing the supervision workflow and graph for a project.

    This agent initializes the supervisor workflow and associated graph, enabling it to manage project
    supervision tasks. It integrates with a language model (LLM) and optionally supports retrieval-augmented
    generation (RAG) for enhanced functionality.
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
        This constructor creates a SupervisorWorkFlow instance to drive the agent's operations, then initializes
        a SupervisorGraph with the specified recursion limit and persistence database path. The agent is then
        constructed using these components.

        Args:
            id (str): Unique identifier for the supervisor agent.
            name (str): Name of the supervisor agent.
            description (str): Brief description of the agent's functionality.
            llm (LLM): An instance of the language model to be used by the agent.
            recursion_limit (int): Maximum recursion depth allowed in the supervisor's graph.
            persistence_db_path (str): Path to the persistence database for saving state and data.
            use_rag (bool, optional): Flag indicating whether to use retrieval-augmented generation (RAG). Defaults to False.
        """
        logger.info(
            "Initializing SupervisorAgent | ID: %s | Name: %s | Recursion Limit: %d | Persistence DB: %s | RAG Enabled: %s",
            id, name, recursion_limit, persistence_db_path, use_rag
        )

        self.work_flow = SupervisorWorkFlow(id, name, llm, use_rag)
        logger.debug("SupervisorWorkFlow initialized for agent: %s", name)

        graph = SupervisorGraph(self.work_flow, recursion_limit, persistence_db_path)
        logger.debug(
            "SupervisorGraph created for agent: %s with recursion_limit=%d and persistence_db_path=%s",
            name, recursion_limit, persistence_db_path
        )

        super().__init__(id, name, description, llm, graph, use_rag)
        
        logger.info("SupervisorAgent successfully initialized | ID: %s | Name: %s", id, name)
    
    @trace_span
    def setup_team(self, team: Team) -> None:
        self.work_flow.setup_team(team)
