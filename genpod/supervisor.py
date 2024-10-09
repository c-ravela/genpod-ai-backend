import warnings
from typing import Any, Dict

from agents.supervisor.supervisor_graph import SupervisorWorkflow
from agents.supervisor.supervisor_state import SupervisorState
from configs.project_config import ProjectAgents
from genpod.member import AgentMember


class SupervisorMember(AgentMember[SupervisorState, SupervisorWorkflow]):
    """
    Represents a supervisor member with additional checks.
    """

    def __init__(self, agents: ProjectAgents, persistance_db_path: str) -> None:
        """
        Initializes the SupervisorMember with specific configurations.
        """
        supervisor_config = agents.supervisor
        super().__init__(
            supervisor_config, 
            SupervisorState, 
            SupervisorWorkflow(supervisor_config.llm, persistance_db_path)
        )
    
    def invoke(self, input: Dict[str, Any] | Any) -> SupervisorState:
        """
        Invokes the base class's invoke method and issues a warning if recursion_limit is -1.
        """
        # Issue a warning if recursion_limit is not set (i.e., -1)
        if self.recursion_limit == -1:
            warnings.warn(
                "Recursion limit is not set (recursion_limit is -1). Consider setting it to a reasonable value.",
                UserWarning
            )
        
        # Proceed with the invocation
        return super().invoke(input)
