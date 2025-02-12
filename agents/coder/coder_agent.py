from agents.coder._internal.coder_graph import CoderGraph
from agents.coder._internal.coder_work_flow import CoderWorkFlow
from core.agent import BaseAgent
from llms import LLM
from utils.logs.logging_utils import logger


class CoderAgent(BaseAgent[CoderGraph]):
    """
    CoderAgent orchestrates the coder workflow using a defined coder graph.
    
    It initializes the workflow and graph components and then passes them to the base agent class
    for further processing.
    """     
    def __init__(
        self,
        id: str,
        name: str,
        llm: LLM,
        recursion_limit: int,
        persistence_db_path: str,
        use_rag: bool = False
    ):
        """
        Initializes the CoderAgent with a coder workflow and its corresponding graph.

        Args:
            id (str): Unique identifier for the agent.
            name (str): Name of the agent.
            llm (LLM): The language model instance to be used.
            recursion_limit (int): Recursion limit for processing the graph.
            persistence_db_path (str): Path to the persistence database.
            use_rag (bool, optional): Flag to determine if retrieval augmented generation should be used. Defaults to False.
        """
        logger.debug(
            "Initializing CoderAgent with id=%s, name=%s, recursion_limit=%d, persistence_db_path=%s, use_rag=%s",
            id, name, recursion_limit, persistence_db_path, use_rag
        )

        work_flow = CoderWorkFlow(id, name, llm, use_rag)

        graph = CoderGraph(work_flow, recursion_limit, persistence_db_path)

        super.__init__(id, name, llm, graph, use_rag)
