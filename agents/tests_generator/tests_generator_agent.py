from agents.tests_generator._internal.tests_generator_graph import \
    TestCoderGraph
from agents.tests_generator._internal.tests_generator_work_flow import \
    TestCoderWorkFlow
from core.agent import BaseAgent
from llms import LLM
from utils.logger import logger


class TestsGeneratorAgent(BaseAgent[TestCoderGraph]):
    """
    Agent responsible for generating tests using the TestCoderGraph workflow.

    This agent leverages the TestCoderWorkFlow and TestCoderGraph to execute test generation tasks.
    It uses a language model (LLM) to process test generation prompts and supports optional retrieval-augmented
    generation (RAG) functionality.
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
        Initialize the TestsGeneratorAgent.

        Args:
            id (str): Unique identifier for the agent.
            name (str): Name of the agent.
            description (str): Brief description of the agent's functionality.
            llm (LLM): The language model instance to be used for generating tests.
            recursion_limit (int): The maximum recursion depth allowed for the graph processing.
            persistence_db_path (str): The file path to the persistence database.
            use_rag (bool, optional): Flag indicating whether to use retrieval-augmented generation. Defaults to False.
        """
        logger.debug(
            "Initializing TestsGeneratorAgent | ID: %s | Name: %s | Recursion Limit: %d | Persistence DB: %s | RAG Enabled: %s",
            id, name, recursion_limit, persistence_db_path, use_rag
        )
        
        work_flow = TestCoderWorkFlow(id, name, llm, use_rag)
        logger.debug("TestCoderWorkFlow initialized for agent: %s", name)
        
        graph = TestCoderGraph(work_flow, recursion_limit, persistence_db_path)
        logger.debug(
            "TestCoderGraph created for agent: %s with recursion_limit=%d and persistence_db_path=%s",
            name, recursion_limit, persistence_db_path
        )

        super().__init__(id, name, description, llm, graph, use_rag)
        
        logger.info("TestsGeneratorAgent successfully initialized | ID: %s | Name: %s", id, name)
