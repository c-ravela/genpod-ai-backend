from agents.tests_generator._internal.tests_generator_graph import \
    TestCoderGraph
from agents.tests_generator._internal.tests_generator_work_flow import \
    TestCoderWorkFlow
from core.agent import BaseAgent
from llms import LLM
from utils.logs.logging_utils import logger


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
        llm: LLM,
        recursion_limit: int,
        persistance_db_path: str,
        use_rag: bool = False
    ):
        """
        Initialize the TestsGeneratorAgent.

        Args:
            id (str): Unique identifier for the agent.
            name (str): Name of the agent.
            llm (LLM): The language model instance to be used for generating tests.
            recursion_limit (int): The maximum recursion depth allowed for the graph processing.
            persistance_db_path (str): The file path to the persistence database.
            use_rag (bool, optional): Flag indicating whether to use retrieval-augmented generation. Defaults to False.
        """
        logger.debug("Initializing TestsGeneratorAgent with id: '%s', name: '%s', recursion_limit: %d, persistance_db_path: '%s', use_rag: %s",
                     id, name, recursion_limit, persistance_db_path, use_rag)
        
        work_flow = TestCoderWorkFlow(id, name, llm, use_rag)
        graph = TestCoderGraph(work_flow, recursion_limit, persistance_db_path)

        super().__init__(id, name, llm, graph, use_rag)
        logger.info("TestsGeneratorAgent '%s' initialized successfully.", name)
