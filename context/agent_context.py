from dataclasses import dataclass, field
from typing import Optional

@dataclass
class AgentContext:
    """A class to represent the context of an agent with logging and best practices."""
   
    agent_id: str
    agent_name: str
    agent_session_id: Optional[str] = field(init=False, default=None)
