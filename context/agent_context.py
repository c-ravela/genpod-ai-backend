from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentContext:
    """A class to represent the context of an agent with logging and best practices."""
   
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
