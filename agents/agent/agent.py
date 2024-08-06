
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI

from typing_extensions import Any
from typing_extensions import Union


class Agent:
    """
    """

    # follow this pattern for creating  a agent id
    # <id>_<name>
    agent_id : str # id for the agent
    agent_name: str # name of the agent
    description: str # description of the agent

    state: Any
    llm: Union[ChatOpenAI, ChatOllama] # This is the language learning model (llm) for the Architect agent. It can be either a ChatOpenAI model or a ChatOllama model

    def __init__(self, agent_id, agent_name, state, llm) -> None:
        """
        """

        self.agent_id = agent_id
        self.agent_name = agent_name
        self.state = state
        self.llm = llm

    def update_state(self, state: Any) -> Any:
        """
        This method updates the current state of the Architect agent with the provided state. 

        Args:
            state (ArchitectState): The new state to update the current state of the agent with.

        Returns:
            ArchitectState: The updated state of the agent.
        """

        self.state = {**state}

        return {**self.state}