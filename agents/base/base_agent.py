from typing import Generic, TypeVar

from typing_extensions import Any

from llms.llm import LLM
from utils.logs.logging_utils import logger

GenericAgentState = TypeVar('GenericAgentState', bound=Any)
GenericPrompts = TypeVar('GenericPrompts', bound=Any)


class BaseAgent(Generic[GenericAgentState, GenericPrompts]):
    """
    Represents an agent equipped with a language learning model (LLM) that can perform various tasks.

    Attributes:
        agent_id (str): A unique identifier for the agent.
        agent_name (str): The name of the agent.
        description (str): A brief description of the agent's purpose or functionality.
        state (GenericAgentState): The current state of the agent, parameterized by a generic type.
        prompts (GenericPrompts): Prompts used by the agent, parameterized by a generic type.
        llm (LLM): The language learning model used by the agent.
    """

    agent_id : str  # Unique identifier for the agent
    agent_name: str  # Name of the agent
    description: str  # Description of the agent's functionality

    state: GenericAgentState  # Current state of the agent
    prompts: GenericPrompts  # Prompts used by the agent
    llm: LLM  # This is the language learning model (llm) for the agent.

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        state: GenericAgentState,
        prompts: GenericPrompts,
        llm: LLM
    ) -> None:
        """
        Initializes the BaseAgent with the specified parameters.

        Args:
            agent_id (str): The unique identifier for the agent.
            agent_name (str): The name of the agent.
            state (GenericAgentState): The initial state of the agent.
            prompts (GenericPrompts): The prompts used by the agent.
            llm (LLM): The language learning model used by the agent.
        """
        logger.info(f"Initializing BaseAgent with ID: {agent_id} and Name: {agent_name}")
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.state = state
        self.prompts = prompts
        self.llm = llm

        logger.debug(f"BaseAgent initialized with state: {state}, prompts: {prompts}, and LLM: {llm}")

    def update_state(self, state: GenericAgentState) -> GenericAgentState:
        """
        Updates the current state of the agent with the provided state.

        Args:
            state (GenericAgentState): The new state to update the agent with.

        Returns:
            GenericAgentState: The updated state of the agent.
        """

        logger.info(f"Updating state for agent {self.agent_name} (ID: {self.agent_id})")
        logger.debug(f"Old state: {self.state}")
        self.state = state
        logger.debug(f"New state: {self.state}")
        return self.state
    
    def __repr__(self) -> str:
        """
        Provides a string representation of the BaseAgent instance.

        Returns:
            str: A string representation of the BaseAgent instance.
        """
        logger.debug(f"Generating string representation for agent {self.agent_name} (ID: {self.agent_id})")
        return f"Agent(id={self.agent_id}, name={self.agent_name}, state={self.state})"

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
