from agents.reviewer.reviewer_graph import ReviewerGraph
from agents.reviewer.reviewer_state import ReviewerState
from configs.project_config import ProjectAgents, ProjectConfig
from genpod.member import AgentMember


class ReviewerMember(AgentMember[ReviewerState, ReviewerGraph]):
    """
    """

    def __init__(self, persistance_db_path: str):
        """
        """

        self.reviewer_config = ProjectConfig().agents_config[ProjectAgents.reviewer.agent_id]
        super().__init__(
            self.reviewer_config,
            ReviewerState,
            ReviewerGraph(self.reviewer_config.llm, persistance_db_path)
        )
