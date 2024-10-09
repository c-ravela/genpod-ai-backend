from agents.architect.architect_graph import ArchitectGraph
from agents.architect.architect_state import ArchitectState
from configs.project_config import ProjectAgents
from genpod.member import AgentMember


class ArchitectMember(AgentMember[ArchitectState, ArchitectGraph]):
    """
    """

    def __init__(self, agents: ProjectAgents, persistance_db_path: str):
        """"""

        architect_config = agents.architect
        super().__init__(
            architect_config, 
            ArchitectState, 
            ArchitectGraph(architect_config.llm, persistance_db_path)
        )
