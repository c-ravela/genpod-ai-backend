from agents.rag_workflow.rag_graph import RAGWorkFlow
from agents.rag_workflow.rag_state import RAGState
from configs.project_config import ProjectAgents
from configs.supervisor_config import VECTOR_DB_COLLECTIONS
from genpod.member import AgentMember


class RagMember(AgentMember[RAGState, RAGWorkFlow]):
    """
    """

    def __init__(self, agents: ProjectAgents, persistance_db_path: str, collection_name: str):
        """"""

        rag_config = agents.rag
        super().__init__(
            rag_config, 
            RAGState, 
            RAGWorkFlow(rag_config.llm, persistance_db_path, collection_name, VECTOR_DB_COLLECTIONS[collection_name])
        )
