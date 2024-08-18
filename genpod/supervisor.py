from agents.supervisor.supervisor_graph import SupervisorWorkflow
from agents.supervisor.supervisor_state import SupervisorState
from configs.project_config import ProjectAgents, ProjectConfig
from genpod.member import AgentMember


class SupervisorMember(AgentMember[SupervisorState, SupervisorWorkflow]):
    """
    """

    def __init__(self, persistance_db_path: str):
        """"""

        self.supervisor_config = ProjectConfig().agents_config[ProjectAgents.supervisor.agent_id]
        super().__init__(
            self.supervisor_config, 
            SupervisorState, 
            SupervisorWorkflow(self.supervisor_config.llm, persistance_db_path)
        )
    