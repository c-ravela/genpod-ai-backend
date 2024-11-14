from agents.architect.architect_graph import ArchitectGraph
from agents.architect.architect_state import ArchitectState
from configs.project_config import ProjectAgents, ProjectGraphs
from genpod.member import AgentMember


class ArchitectMember(AgentMember[ArchitectState, ArchitectGraph]):
    """
    """

    def __init__(self, agents: ProjectAgents, graphs: ProjectGraphs, persistance_db_path: str):
        """"""

        architect_config = agents.architect
        architect_graph = graphs.architect
        super().__init__(
            architect_config, 
            ArchitectState, 
            ArchitectGraph(
                architect_graph.graph_id, 
                architect_graph.graph_name,
                architect_config.agent_id,
                architect_config.agent_name,
                architect_config.llm,
                persistance_db_path
            )
        )
