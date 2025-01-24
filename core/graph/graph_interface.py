from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator


class IGraph(ABC):
    """
    Interface for all graphs.
    """

    @abstractmethod
    def invoke(self, input_data: Dict[str, Any], state: Any) -> Any:
        """
        Executes a graph node based on input data and current state.

        Args:
            input_data (Dict[str, Any]): Input data for the graph.
            state (Any): Current state of the agent.

        Returns:
            Any: The result of the graph invocation.
        """
        pass

    @abstractmethod
    def stream(self, input_data: Dict[str, Any], state: Any) -> Iterator[Any]:
        """
        Streams responses from the graph based on input data and state.

        Args:
            input_data (Dict[str, Any]): Input data for the graph.
            state (Any): Current state of the agent.

        Yields:
            Any: Streamed responses.
        """
        pass
