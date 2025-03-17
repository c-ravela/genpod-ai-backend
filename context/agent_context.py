from dataclasses import dataclass, field

@dataclass
class AgentContext:
    """A class to represent the context of an agent."""
   
    agent_id: str
    agent_name: str
    agent_session_id: str = field(init=False, default=None)
