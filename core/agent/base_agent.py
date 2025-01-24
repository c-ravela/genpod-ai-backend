from abc import ABC, abstractmethod
from typing import Any

from core.agent import IAgent
from core.state import IState
from llms.llm import LLM
from utils.logs.logging_utils import logger


class BaseAgent(IAgent, ABC):
    """
    Abstract base class for all agents, implementing common functionalities.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        prompts: str,
        llm: LLM,
        use_rag: bool = False
    ) -> None:
        """
        Initializes the BaseAgent.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Human-readable name for the agent.
            state (BaseState): The initial state of the agent.
            prompts (BasePrompt): The prompts used by the agent.
            llm (LLM): Language Learning Model instance.
            use_rag (bool, optional): Flag to enable RAG interactions. Defaults to False.
        """
        logger.info(f"Initializing {self.__class__.__name__} with agent_id='{agent_id}' and agent_name='{agent_name}'")
        self._agent_id = agent_id
        self._agent_name = agent_name
        self.prompts = prompts
        self.llm = llm
        self.use_rag = use_rag
        logger.info(f"Initialized {self.__class__.__name__} successfully.")

    @property
    def agent_id(self) -> str:
        """
        Gets the agent's unique identifier.

        Returns:
            str: The agent's ID.
        """
        logger.debug(f"Accessing 'agent_id' for {self.__class__.__name__}: '{self._agent_id}'")
        return self._agent_id

    @property
    def agent_name(self) -> str:
        """
        Gets the agent's name.

        Returns:
            str: The agent's name.
        """
        logger.debug(f"Accessing 'agent_name' for {self.__class__.__name__}: '{self._agent_name}'")
        return self._agent_name

    @abstractmethod
    def router(self, state: 'BaseState') -> str:
        """
        Abstract method to determine the routing logic based on the agent's state.

        Args:
            state (BaseState): The current state of the agent.

        Returns:
            str: The routing decision or response.
        """
        pass

    @staticmethod
    def ensure_value(value: Any, fallback: Any) -> Any:
        """
        Ensures the value is not None by returning it if present,
        or the fallback value otherwise.

        Args:
            value (Any): The input value to check.
            fallback (Any): The fallback value to return if the input value is None.

        Returns:
            Any: Either the provided value or the fallback value.
        """
        if value is not None:
            logger.debug(f"Value provided: {value}")
            return value
        else:
            logger.warning(f"Value is None, returning fallback: {fallback}")
            return fallback

    def __repr__(self) -> str:
        """
        Returns a string representation of the BaseAgent instance.

        Returns:
            str: The string representation.
        """
        logger.debug(f"Generating string representation for agent {self.agent_name} (ID: {self.agent_id})")
        return (
            f"{self.__class__.__name__}("
            f"agent_id={self.agent_id!r}, "
            f"agent_name={self.agent_name!r}, "
            f"prompts={self.prompts!r}, "
            f"llm={self.llm!r}, "
            f"use_rag={self.use_rag!r}"
            f")"
        )
