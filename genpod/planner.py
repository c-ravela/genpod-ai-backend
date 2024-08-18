from agents.planner.planner_graph import PlannerWorkFlow
from agents.planner.planner_state import PlannerState
from configs.project_config import ProjectAgents, ProjectConfig
from genpod.member import AgentMember


class PlannerMember(AgentMember[PlannerState, PlannerWorkFlow]):
    """
    """

    def __init__(self, persistance_db_path: str):
        """"""

        self.plnr_config = ProjectConfig().agents_config[ProjectAgents.planner.agent_id]
        super().__init__(
            self.plnr_config, 
            PlannerState, 
            PlannerWorkFlow(self.plnr_config.llm, persistance_db_path)
        )
    