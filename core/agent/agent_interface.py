from abc import ABC, abstractmethod
from typing import Any


class IAgent(ABC):
    """
    Interface for all agents.
    """

    @property
    @abstractmethod
    def agent_id(self) -> str:
        """Unique identifier for the agent."""
        pass

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Human-readable name for the agent."""
        pass

    @abstractmethod
    def router(self, state: Any) -> str:
        """
        Determines the next node or action based on the current state.

        Args:
            state (Any): The current state of the agent.

        Returns:
            str: The identifier of the next node or action.
        """
        pass
