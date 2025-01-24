from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator

from langgraph.graph import StateGraph

from core.agent import IAgent
from core.graph import IGraph


class BaseGraph(IGraph, ABC):
    """
    Abstract base class for all graphs, implementing common functionalities.
    """

    def __init__(
        self,
        graph_id: str,
        graph_name: str,
        agent: 'IAgent',
        persistence_db_path: str
    ) -> None:
        """
        Initializes the BaseGraph.

        Args:
            graph_id (str): Unique identifier for the graph.
            graph_name (str): Human-readable name for the graph.
            agent (IAgent): The agent associated with this graph.
            persistence_db_path (str): Path to the persistence database.
        """
        self.graph_id = graph_id
        self.graph_name = graph_name
        self.agent = agent
        self.persistence_db_path = persistence_db_path
        self.state_graph: StateGraph = self.define_graph()
        self.compile_graph_with_persistence()

    @abstractmethod
    def define_graph(self) -> StateGraph:
        """
        Defines the state graph structure.

        Returns:
            StateGraph: The defined state graph.
        """
        pass

    def compile_graph_with_persistence(self) -> None:
        """
        Compiles the graph and integrates persistence mechanisms.
        """
        # Implement persistence logic here
        pass

    @abstractmethod
    def invoke(self, input_data: Dict[str, Any], state: Any) -> Any:
        pass

    @abstractmethod
    def stream(self, input_data: Dict[str, Any], state: Any) -> Iterator[Any]:
        pass
