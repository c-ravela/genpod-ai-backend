from agents.research._internal.research_graph import ResearchGraph
from agents.research._internal.research_work_flow import ResearchWorkFlow
from core.agent import BaseAgent
from llms import LLM
from utils.logger import logger


class ResearchAgent(BaseAgent[ResearchGraph]):
    """
    ResearchAgent is responsible for conducting in-depth research by leveraging a dedicated research workflow
    and its associated state graph. It processes research queries through multiple stages such as query evaluation,
    source-based research, open web research, response refinement, and final response generation.

    Attributes:
        id (str): Unique identifier for the agent.
        name (str): Human-readable name of the agent.
        description (str): Brief description of the agent's role and functionality.
        llm (LLM): Instance of the language model used throughout the research workflow.
        graph (ResearchGraph): The state graph that orchestrates the research workflow.
    """

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        llm: LLM,
        recursion_limit: int,
        persistence_db_path: str
    ):
        """
        Initializes the ResearchAgent with the specified parameters.

        This constructor sets up the research workflow and constructs a corresponding state graph using the given
        recursion limit and persistence database path. It then initializes the agent by passing the constructed
        graph and other parameters to the BaseAgent constructor.

        Args:
            id (str): The unique identifier for the agent.
            name (str): The name of the agent.
            description (str): A brief description of the agent's role.
            llm (LLM): The language model instance used for processing research queries.
            recursion_limit (int): The maximum recursion depth allowed for the state graph.
            persistence_db_path (str): The file path to the persistence database for storing the workflow state.
        """
        logger.info("Initializing ResearchAgent with id: %s, name: %s", id, name)
        
        work_flow = ResearchWorkFlow(id, name, llm)
        logger.debug("ResearchWorkFlow initialized for agent '%s'.", name)
        
        graph = ResearchGraph(work_flow, recursion_limit, persistence_db_path)
        logger.debug("ResearchGraph constructed with recursion_limit=%d, persistence_db_path='%s'.", recursion_limit, persistence_db_path)
        
        super().__init__(id, name, description, llm, graph)
        logger.info("ResearchAgent '%s' initialized successfully.", name)
