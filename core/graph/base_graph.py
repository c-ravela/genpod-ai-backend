import io
import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, TypeVar

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from PIL import Image

from core.workflow import BaseWorkFlow
from utils.decorators import auto_repr
from utils.logs.logging_utils import logger

GenericAgentWorkFlow = TypeVar("GenericAgentWorkFlow", bound=BaseWorkFlow)


@auto_repr
class BaseGraph(ABC, Generic[GenericAgentWorkFlow]):
    """
    Abstract base class for all graphs, implementing common functionalities including
    compilation, persistence, and state management. The graph is immediately compiled
    during initialization and can be invoked or streamed, provided that a valid thread ID
    is set via the set_thread_id() method.
    """

    def __init__(
        self,
        work_flow: GenericAgentWorkFlow,
        recursion_limit: int,
        persistence_db_path: str
    ) -> None:
        """
        Initializes the BaseGraph.

        Args:
            work_flow (GenericAgentWorkFlow): The workflow associated with this graph.
            recursion_limit (int): Maximum recursion depth for processing. Must be a positive integer.
            persistence_db_path (str): Path to the persistence database. Must be a non-empty string.

        Raises:
            ValueError: If recursion_limit is not a positive integer or persistence_db_path is invalid.
        """
        logger.info("Initializing BaseGraph with recursion_limit=%s and persistence_db_path=%s",
                    recursion_limit, persistence_db_path)

        if not isinstance(recursion_limit, int) or recursion_limit <= 0:
            raise ValueError("recursion_limit must be a positive integer.")
        
        if not isinstance(persistence_db_path, str) or not persistence_db_path:
            raise ValueError("A valid persistence_db_path must be provided.")

        self.work_flow = work_flow
        self.recursion_limit = recursion_limit
        self.__sqlite_con = sqlite3.connect(persistence_db_path, check_same_thread=False)
        self.__state_saver = SqliteSaver(self.__sqlite_con)

        logger.info("Memory (SqliteSaver) initialized successfully.")

        self.thread_id = None
        self.__compiled_graph: CompiledGraph = None

        self._compile_graph_with_persistence()

    @abstractmethod
    def define_graph(self) -> StateGraph:
        """
        Defines the state graph structure.

        Returns:
            StateGraph: The defined state graph.
        """
        pass

    def _compile_graph_with_persistence(self) -> None:
        """
        Compiles the graph defined by `define_graph` and persists it using SqliteSaver.

        The method logs the compilation process and ensures that the graph is compiled only once.
        
        Raises:
            RuntimeError: If the graph has already been compiled or if compilation fails.
        """
        if self.__compiled_graph is not None:
            logger.error(
                f"Graph has already been compiled. Current compiled graph: {self.__compiled_graph}"
            )
            raise RuntimeError(
                f"Graph has already been compiled. Current compiled graph: {self.__compiled_graph}"
            )

        try:
            logger.info("Starting graph compilation with persistence.")
            defined_graph = self.define_graph()
            if defined_graph is None:
                logger.error("define_graph() returned None; a valid StateGraph is required.")
                raise RuntimeError("define_graph() returned None; a valid StateGraph is required.")
           
            self.__compiled_graph = defined_graph.compile(checkpointer=self.__state_saver)
            logger.info("Graph compilation completed successfully. Compiled graph: %s", self.__compiled_graph)
        except Exception as e:
            logger.error("An error occurred during graph compilation. %s", e)
            raise RuntimeError(f"Graph compilation failed: {e}") from e

    def _build_graph_config(self) -> Dict[str, Any]:
        """
        Builds the configuration dictionary for the graph.

        Returns:
            Dict[str, Any]: A dictionary containing configuration parameters for the graph,
                            including the recursion limit and current thread_id.
        """
        return {
            "recursion_limit": self.recursion_limit,
            "configurable": {
                "thread_id": self.thread_id
            }
        }

    @property
    def graph_config(self) -> Dict[str, Any]:
        """
        Returns the graph configuration as a dictionary.

        This property rebuilds the configuration each time it is accessed, allowing for
        dynamic changes in configuration such as an updated thread_id.

        Returns:
            Dict[str, Any]: The configuration dictionary for the graph.
        """
        return self._build_graph_config()
    
    def get_last_saved_state(self) -> Dict[str, Any]:
        """
        Retrieves the last saved state of the workflow using the current graph configuration.

        Returns:
            Dict[str, Any]: The saved state of the workflow as retrieved from the graph's application.

        Raises:
            RuntimeError: If the graph's application (.__compiled_graph) is not initialized.
        """
        if self.__compiled_graph is None:
            logger.error("Graph has not been compiled yet.")
            raise RuntimeError("Graph has not been compiled yet.")
        logger.info("Retrieving last saved state using graph configuration: %s", self.graph_config)
        return self.__compiled_graph.get_state(self.graph_config).values

    def display_graph(self) -> None:
        """
        Displays the graph visually by rendering it as an image and showing it.

        Raises:
            RuntimeError: If the graph has not been compiled yet.
            Exception: If there is an error in rendering or displaying the graph.
        """
        if self.__compiled_graph is None:
            logger.error("Graph has not been compiled yet.")
            raise RuntimeError("Graph has not been compiled yet.")

        logger.info("Attempting to display the graph visually.")
        try:
            img = Image.open(io.BytesIO(self.__compiled_graph.get_graph().draw_mermaid_png()))
            img.show()
            logger.info("Graph displayed successfully.")
        except Exception as e:
            logger.exception("Failed to display graph: %s", e, exc_info=True)

    def stream(self, input_data: Any) -> Any:
        """
        Streams the input data through the graph's execution pipeline.

        Args:
            input_data (Any): The input data to be processed.

        Returns:
            Any: The result of streaming the input data.

        Raises:
            ValueError: If thread_id is not initialized.
        """
        if self.thread_id is None:
            raise ValueError("Graph thread_id has not been initialized. "
                             "Ensure that set_thread_id() is called with a valid thread ID before invoking stream.")
        logger.info("Streaming input data through the graph. Thread ID: %s, Input: %s", self.thread_id, input_data)
        return self.__compiled_graph.stream(input_data, self.graph_config)

    def invoke(self, input_data: Any) -> Any:
        """
        Invokes the graph's execution with the provided input.

        Args:
            input_data (Any): The input data to be processed.

        Returns:
            Any: The result of invoking the graph.

        Raises:
            ValueError: If thread_id is not initialized.
        """
        if self.thread_id is None:
            raise ValueError("Graph thread_id has not been initialized. "
                             "Ensure that set_thread_id() is called with a valid thread ID before invoking invoke.")
        logger.debug("Invoking graph execution. Thread ID: %s, Input: %s", self.thread_id, input_data)
        return self.__compiled_graph.invoke(input_data, self.graph_config)

    def set_thread_id(self, thread_id: int) -> None:
        """
        Sets the thread ID for the graph after performing validation.

        Args:
            thread_id (int): The thread ID to be set. Must be a positive integer.

        Raises:
            ValueError: If the thread_id is not a positive integer.
        """
        logger.info("Attempting to set thread_id to: %s", thread_id)
        if not isinstance(thread_id, int):
            raise ValueError(
                f"Invalid thread_id provided: {thread_id} (type: {type(thread_id).__name__}). "
                "Expected a positive integer."
            )
        if thread_id <= 0:
            raise ValueError(
                f"Invalid thread_id provided: {thread_id}. "
                "Expected a positive integer greater than zero."
            )
        self.thread_id = thread_id
        logger.info("Thread ID set successfully to: %s", self.thread_id)
