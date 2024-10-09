from agents.reviewer.reviewer_graph import ReviewerGraph
from agents.reviewer.reviewer_state import ReviewerState
from configs.project_config import ProjectAgents, ProjectGraphs
from genpod.member import AgentMember


class ReviewerMember(AgentMember[ReviewerState, ReviewerGraph]):
    """
    """

    def __init__(self, agents: ProjectAgents, graphs: ProjectGraphs, persistance_db_path: str):
        """
        """

        reviewer_config = agents.reviewer
        reviewer_graph = graphs.reviewer
        super().__init__(
            reviewer_config,
            ReviewerState,
            ReviewerGraph(
                reviewer_graph.graph_id,
                reviewer_graph.graph_name,
                reviewer_config.agent_id,
                reviewer_config.agent_name,
                reviewer_config.llm, 
                persistance_db_path
            )
        )
