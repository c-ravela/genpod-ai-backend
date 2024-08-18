from agents.rag_workflow.rag_graph import RAGWorkFlow
from agents.rag_workflow.rag_state import RAGState
from configs.project_config import ProjectAgents, ProjectConfig
from configs.supervisor_config import VECTOR_DB_COLLECTIONS
from genpod.member import AgentMember


class RagMember(AgentMember[RAGState, RAGWorkFlow]):
    """
    """

    def __init__(self, persistance_db_path: str, collection_name: str):
        """"""

        self.rag_config = ProjectConfig().agents_config[ProjectAgents.rag.agent_id]
        super().__init__(
            self.rag_config, 
            RAGState, 
            RAGWorkFlow(self.rag_config.llm, persistance_db_path, collection_name, VECTOR_DB_COLLECTIONS[collection_name])
        )
    