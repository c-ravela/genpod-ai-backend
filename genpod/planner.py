from agents.planner.planner_graph import PlannerWorkFlow
from agents.planner.planner_state import PlannerState
from configs.project_config import ProjectAgents
from genpod.member import AgentMember


class PlannerMember(AgentMember[PlannerState, PlannerWorkFlow]):
    """
    """

    def __init__(self, agents: ProjectAgents, persistance_db_path: str):
        """"""

        plnr_config = agents.planner
        super().__init__(
            plnr_config, 
            PlannerState, 
            PlannerWorkFlow(plnr_config.llm, persistance_db_path)
        )
