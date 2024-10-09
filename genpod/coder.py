from agents.coder.coder_graph import CoderGraph
from agents.coder.coder_state import CoderState
from configs.project_config import ProjectAgents
from genpod.member import AgentMember


class CoderMember(AgentMember[CoderState, CoderGraph]):
    """
    """

    def __init__(self, agents: ProjectAgents, persistance_db_path: str):
        """"""

        coder_config = agents.coder
        super().__init__(
            coder_config, 
            CoderState, 
            CoderGraph(coder_config.llm, persistance_db_path)
        )
   