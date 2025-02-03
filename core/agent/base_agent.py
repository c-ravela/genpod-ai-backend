from typing import Any, Dict, Generic, TypeVar

from core.graph import BaseGraph
from llms import LLM
from utils.decorators import auto_repr
from utils.logs.logging_utils import logger

GenericAgentGraph = TypeVar('GenericAgentGraph', bound=BaseGraph)


@auto_repr
class BaseAgent(Generic[GenericAgentGraph]):
    """
    Base agent that interacts with a graph and a language model (LLM).
    """

    def __init__(
        self,
        id: str,
        name: str,
        llm: LLM,
        graph: GenericAgentGraph,
        use_rag: bool = False
    ):
        """
        Initializes the BaseAgent.

        Args:
            id (str): Unique identifier for the agent.
            name (str): Human-readable name for the agent.
            llm (LLM): Instance of a language model.
            graph (GenericAgentGraph): The graph associated with this agent.
            use_rag (bool, optional): Flag to enable retrieval-augmented generation. Defaults to False.
        """
        logger.info("Initializing BaseAgent with id: %s, name: %s, use_rag: %s", id, name, use_rag)
        self.id = id
        self.name = name
        self.llm = llm
        self.graph = graph
        self.use_rag = use_rag

    def stream(self, input_data: Any) -> Any:
        """
        Streams input data by delegating to the graph's stream method.

        Args:
            input_data (Any): The input data to be processed.

        Returns:
            Any: The result of streaming the input data through the graph.
        """
        logger.debug("Agent %s streaming input data: %s", self.id, input_data)
        result = self.graph.stream(input_data)
        logger.debug("Agent %s received streaming result: %s", self.id, result)
        return result

    def invoke(self, input_data: Any) -> Any:
        """
        Invokes the graph by delegating to the graph's invoke method.

        Args:
            input_data (Any): The input data to be processed.

        Returns:
            Any: The result of invoking the graph.
        """
        logger.debug("Agent %s invoking graph with input: %s", self.id, input_data)
        result = self.graph.invoke(input_data)
        logger.debug("Agent %s received invocation result: %s", self.id, result)
        return result

    def set_thread_id(self, thread_id: int) -> None:
        """
        Sets the thread (execution) ID for the graph by delegating to the graph's set_thread_id method.

        Args:
            thread_id (int): A positive integer representing the thread (execution) ID.
        """
        logger.info("Agent %s setting thread_id to: %s", self.id, thread_id)
        self.graph.set_thread_id(thread_id)
        logger.info("Agent %s thread_id successfully set to: %s", self.id, thread_id)

    def show_graph(self) -> None:
        """
        Displays the graph visually by delegating to the graph's display_graph method.
        """
        logger.info("Agent %s displaying graph.", self.id)
        self.graph.display_graph()
        logger.info("Agent %s has finished displaying the graph.", self.id)
    
    @property
    def runtime_config(self) -> Dict[str, Any]:
        """
        Returns the runtime configuration of the graph.

        This property provides access to the configuration (previously called graph_config)
        from the underlying graph.

        Returns:
            Dict[str, Any]: The configuration dictionary for the graph.
        """
        logger.info("Agent %s retrieving runtime configuration.", self.id)
        config = self.graph.graph_config
        logger.debug("Agent %s runtime configuration: %s", self.id, config)
        return config

    def retrieve_last_state(self) -> Dict[str, Any]:
        """
        Retrieves the last saved state of the workflow from the graph.

        Returns:
            Dict[str, Any]: The last saved state as retrieved from the underlying graph.
        """
        logger.info("Agent %s retrieving last saved state from graph.", self.id)
        state = self.graph.get_last_saved_state()
        logger.info("Agent %s retrieved last saved state: %s", self.id, state)
        return state
