import io
from typing import Any, Generic, TypeVar

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from PIL import Image

from utils.logs.logging_utils import logger

GenericAgent = TypeVar('GenericAgent', bound=Any)


class BaseGraph(Generic[GenericAgent]):
    """
    Base class for defining and managing state graphs.

    Attributes:
        id (str): Unique identifier for the graph.
        name (str): Name of the graph.
        agent (GenericAgent): The agent associated with the graph.
        memory (SqliteSaver): Mechanism for saving the graph state persistently.
        app (CompiledGraph): The compiled state graph.
    """

    name: str
    id: str
    agent: GenericAgent
    memory: SqliteSaver
    app: CompiledGraph

    def __init__(
        self,
        id: str,
        name: str,
        agent: GenericAgent,
        persistence_db_path: str
    ) -> None:
        """
        Initializes the BaseGraph instance.

        Args:
            id (str): Unique identifier for the graph.
            name (str): Name of the graph.
            agent (GenericAgent): The agent associated with the graph.
            persistence_db_path (str): Path to the SQLite database for persistence.
        """
        logger.info(f"Initializing BaseGraph with ID: {id} and Name: {name}")
        self.id = id
        self.name = name
        self.agent = agent
        self.memory = SqliteSaver.from_conn_string(persistence_db_path)
        self.app = None
        logger.debug(f"BaseGraph initialized with persistence DB at: {persistence_db_path}")

    def compile_graph_with_persistence(self) -> None:
        """
        Compiles the graph defined by `define_graph` and persists it using `SqliteSaver`.

        Raises:
            RuntimeError: If the graph is already compiled.
        """
        if self.app is None:
            logger.info(f"Compiling graph '{self.name}' with persistence enabled.")
            self.app = self.define_graph().compile(checkpointer=self.memory)
            logger.debug("Graph compiled successfully.")
        else:
            logger.error("Attempted to compile an already compiled graph.")
            raise RuntimeError("Graph has already been compiled.")

    def display_graph(self) -> None:
        """
        Displays the graph visually. The graph is rendered as an image and shown.

        Raises:
            RuntimeError: If the graph has not been compiled yet.
        """
        if self.app is None:
            logger.error("Cannot display graph because it has not been compiled.")
            raise RuntimeError("Graph has not been compiled yet.")

        try:
            logger.info(f"Displaying graph '{self.name}' visually.")
            img = Image.open(io.BytesIO(self.app.get_graph().draw_mermaid_png()))
            img.show()
            logger.debug("Graph displayed successfully.")
        except Exception as e:
            logger.error(f"Failed to display graph: {e}", exc_info=True)

    def define_graph(self) -> StateGraph:
        """
        Defines the state graph for the agent.

        Returns:
            StateGraph: The state graph for the agent.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        logger.error("define_graph() must be implemented by subclasses.")
        raise NotImplementedError("Subclasses must implement this method.")
    
    def get_current_state(self) -> Any:
        """
        Fetches the current state of the graph.

        Returns:
            Any: The current state of the agent.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        logger.error("get_current_state() must be implemented by subclasses.")
        raise NotImplementedError("Subclasses must implement this method.")

    def __repr__(self) -> str:
        """
        Provides a string representation of the Graph instance.

        Returns:
            str: A string representation of the Graph instance.
        """
        logger.debug(f"Generating string representation for graph '{self.name}' (ID: {self.id})")
        return f"Graph(id={self.id}, name={self.name}, agent={self.agent})"
