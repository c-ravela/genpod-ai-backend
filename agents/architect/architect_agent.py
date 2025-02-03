from agents.architect._internal.architect_graph import ArchitectGraph
from agents.architect._internal.architect_work_flow import ArchitectWorkFlow
from core.agent import BaseAgent
from llms import LLM


class ArchitectAgent(BaseAgent[ArchitectGraph]):
    
    def __init__(
        self,
        id: str,
        name: str,
        llm: LLM,
        recursion_limit: int,
        persistance_db_path: str,
        use_rag: bool = False
    ):
        
        work_flow = ArchitectWorkFlow(id, name, llm, use_rag)

        super().__init__(
            id,
            name,
            llm,
            ArchitectGraph(
                work_flow,
                recursion_limit,
                persistance_db_path
            ),
            use_rag
        )
