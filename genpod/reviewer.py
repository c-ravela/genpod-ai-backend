from agents.reviewer.reviewer_graph import ReviewerGraph
from agents.reviewer.reviewer_state import ReviewerState
from configs.project_config import ProjectAgents
from genpod.member import AgentMember


class ReviewerMember(AgentMember[ReviewerState, ReviewerGraph]):
    """
    """

    def __init__(self, agents: ProjectAgents, persistance_db_path: str):
        """
        """

        reviewer_config = agents.reviewer
        super().__init__(
            reviewer_config,
            ReviewerState,
            ReviewerGraph(reviewer_config.llm, persistance_db_path)
        )
