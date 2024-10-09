from agents.planner.planner_graph import PlannerWorkFlow
from agents.planner.planner_state import PlannerState
from configs.project_config import ProjectAgents, ProjectGraphs
from genpod.member import AgentMember


class PlannerMember(AgentMember[PlannerState, PlannerWorkFlow]):
    """
    """

    def __init__(self, agents: ProjectAgents, graphs: ProjectGraphs, persistance_db_path: str):
        """"""

        plnr_config = agents.planner
        plnr_grph = graphs.planner
        super().__init__(
            plnr_config, 
            PlannerState, 
            PlannerWorkFlow(
                plnr_grph.graph_id,
                plnr_grph.graph_name,
                plnr_config.agent_id,
                plnr_config.agent_name,
                plnr_config.llm, 
                persistance_db_path
            )
        )
