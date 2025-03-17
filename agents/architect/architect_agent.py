from agents.architect._internal.architect_graph import ArchitectGraph
from agents.architect._internal.architect_work_flow import ArchitectWorkFlow
from core.agent import BaseAgent
from llms import LLM
from utils.logs.logging_utils import logger


class ArchitectAgent(BaseAgent[ArchitectGraph]):
    """
    ArchitectAgent is responsible for managing an architectural workflow 
    using a specified LLM model, recursion limits, and persistence settings.
    
    It extends the BaseAgent class with a specialized graph structure for
    executing complex workflows.
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
        Initializes an ArchitectAgent with the required configurations.
        
        Args:
            id (str): Unique identifier for the agent.
            name (str): Name of the agent.
            description (str): Brief description of the agent.
            llm (LLM): The LLM model used for processing.
            recursion_limit (int): Maximum recursion depth for workflow execution.
            persistence_db_path (str): Path to the persistence database.
            use_rag (bool, optional): Flag to enable RAG (Retrieval-Augmented Generation). Defaults to False.
        """
        logger.info(f"Initializing ArchitectAgent: {name} (ID: {id})")
            
        work_flow = ArchitectWorkFlow(id, name, llm, use_rag)
        graph = ArchitectGraph(work_flow, recursion_limit, persistence_db_path)

        super().__init__(id, name, description, llm, graph, use_rag)
        
        logger.info(f"ArchitectAgent '{name}' initialized successfully.")
