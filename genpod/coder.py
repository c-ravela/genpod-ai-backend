from agents.coder.coder_graph import CoderGraph
from agents.coder.coder_state import CoderState
from configs.project_config import ProjectAgents, ProjectGraphs
from genpod.member import AgentMember


class CoderMember(AgentMember[CoderState, CoderGraph]):
    """
    """

    def __init__(self, agents: ProjectAgents, graphs: ProjectGraphs, persistance_db_path: str):
        """"""

        coder_config = agents.coder
        coder_graph = graphs.coder
        super().__init__(
            coder_config, 
            CoderState, 
            CoderGraph(
                coder_graph.graph_id, 
                coder_graph.graph_name, 
                coder_config.agent_id,
                coder_config.agent_name,
                coder_config.llm, 
                persistance_db_path
            )
        )
