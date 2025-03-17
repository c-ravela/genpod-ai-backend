from dataclasses import dataclass
from typing import List, Optional

from core.agent import BaseAgent
from utils.logs.logging_utils import logger


@dataclass
class RagAgentEntry:
    """
    Data class for holding a RAG agent and its description.
    """
    agent: Optional[BaseAgent] = None
    description: Optional[str] = ""


class RagAgentRegistry:
    """
    Registry for RAG agents. This class maintains a list of registered RAG agents
    along with their descriptions.
    """
    def __init__(self) -> None:
        self.entries: List[RagAgentEntry] = []
        logger.info("Initialized %s with an empty entries list.", self.__class__.__name__)

    def register(self, agent: BaseAgent, description: str):
        """
        Register a new RAG agent along with a description.
        
        Args:
            agent (BaseAgent): An instance of a RAG agent that is a subclass of BaseAgent.
            description (str): A description of the type of questions this agent can answer.
            
        Raises:
            TypeError: If the provided agent is not an instance of BaseAgent.
        """
        if not isinstance(agent, BaseAgent):
            logger.error("Attempted to register an agent that is not an instance of BaseAgent: %s", agent)
            raise TypeError("Agent must be an instance of BaseAgent")
        entry = RagAgentEntry(agent=agent, description=description)
        self.entries.append(entry)
        logger.info("Registered RAG agent: %s", agent.name)
        logger.debug("Registered RAG agent: %s with description: '%s'", agent, description)

    def get_agents(self):
        """
        Return all registered RAG agent entries.
        
        Returns:
            List[RagAgentEntry]: A list of all registered agents along with their descriptions.
        """
        logger.debug("Retrieving all registered RAG agent entries. Count: %d", len(self.entries))
        return self.entries

    def count(self) -> int:
        """
        Return the number of registered RAG agents.
        
        Returns:
            int: The count of registered RAG agents.
        """
        count = len(self.entries)
        logger.debug("Current registered agent count: %d", count)
        return count

# Create a single registry instance for the module.
_registry = RagAgentRegistry()

def register_rag_agent(agent: BaseAgent, description: str):
    """
    Register a RAG agent instance with its description.

    Args:
        agent (BaseAgent): An instance of a RAG agent.
        description (str): A description of the questions this agent can answer.
    """
    logger.debug("register_rag_agent() called for agent: %s", agent.name)
    _registry.register(agent, description)

def get_rag_agents():
    """
    Retrieve the list of registered RAG agent entries.
    
    Returns:
        List[RagAgentEntry]: The list of RAG agent entries.
    """

    agents = _registry.get_agents()
    logger.debug("get_rag_agents() returning %d agents", len(agents))
    return agents

def get_registered_agent_count() -> int:
    """
    Retrieve the count of registered RAG agents.
    
    Returns:
        int: The number of registered RAG agents.
    """
    count = _registry.count()
    logger.debug("get_registered_agent_count() returning count: %d", count)
    return count
