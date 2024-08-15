from typing import Union, Dict, Type
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI
from agents.architect.graph import ArchitectGraph
from agents.architect.state import ArchitectState
from agents.coder.graph import CoderGraph
from agents.coder.state import CoderState
from agents.planner.planner_graph import PlannerWorkFlow
from agents.planner.planner_state import PlannerState
from agents.rag_workflow.rag_graph import RAGWorkFlow
from agents.rag_workflow.rag_state import RAGState
from configs.project_config import AgentConfig, ProjectAgents
from typing_extensions import TypedDict
from agents.supervisor.supervisor_state import SupervisorState
from agents.supervisor.supervisor_graph import SupervisorWorkflow
from agents.agent.state import State
from agents.agent.graph import Graph

class AgentMember:
    """
    Represents an individual agent with its configuration and state.
    """

    member_id: str
    member_name: str
    llm: Union[ChatOpenAI, ChatOllama]
    thread_id: int
    fields: list[str]
    in_fields: list[str]
    out_fields: list[str]
    inout_fields: list[str]
    graph: Graph
    max_retries: int = 3
    
    def __init__(self, agent_config: AgentConfig, state_class: Type[TypedDict], graph: Graph) -> None:
        """
        Initializes an AgentMember instance with the given configuration and state.
        """
        self.member_id = agent_config.agent_id
        self.member_name = agent_config.agent_name
        self.llm = agent_config.llm
        self.thread_id = agent_config.thread_id

        sc = State(state_class)
        self.fields = sc.get_fields()
        self.in_fields = sc.get_in_fields()
        self.out_fields = sc.get_out_fields()
        self.inout_fields = sc.get_inout_fields()

        self.graph = graph
    
    def __str__(self) -> str:
        """
        Returns a user-friendly string representation of the object.
        """
        return (f"AgentMember(member_id={self.member_id!r}, "
                f"member_name={self.member_name!r}, "
                f"llm_type={type(self.llm).__name__}, "
                f"thread_id={self.thread_id}, "
                f"fields={self.fields}, "
                f"in_fields={self.in_fields}, "
                f"out_fields={self.out_fields}, "
                f"inout_fields={self.inout_fields}, "
                f"graph_type={type(self.graph).__name__})")

class TeamMembers:
    """
    Manages a team of different agents.
    """

    def __init__(self, collections: Dict[str, str], agents_config: Dict[str, AgentConfig], persistance_db_path: str) -> None:
        """
        Initializes the team members with their configurations and state/graph setups.
        """
        self.collections = collections
        self.agent_config = agents_config
        self.persistance_db_path = persistance_db_path

        # Define the state and graph classes for each agent type
        self.agent_definitions = {
            ProjectAgents.supervisor.agent_id: (SupervisorState, SupervisorWorkflow),
            ProjectAgents.architect.agent_id: (ArchitectState, ArchitectGraph),
            ProjectAgents.coder.agent_id: (CoderState, CoderGraph),
            ProjectAgents.rag.agent_id: (RAGState, RAGWorkFlow),
            ProjectAgents.planner.agent_id: (PlannerState, PlannerWorkFlow),
        }

        self.architect = self._create_agent(ProjectAgents.architect.agent_id)
        self.coder = self._create_agent(ProjectAgents.coder.agent_id)
        self.rag = self._create_agent(ProjectAgents.rag.agent_id, rag_collection=True)
        self.planner = self._create_agent(ProjectAgents.planner.agent_id)

    def _create_agent(self, agent_id: str, rag_collection: bool = False) -> AgentMember:
        """
        Creates an agent member based on its ID and the definitions provided.
        """
        state_class, graph_class = self.agent_definitions[agent_id]
        agent_config = self.agent_config[agent_id]
        graph_params = (agent_config.llm, self.persistance_db_path,)

        if rag_collection:
            # Special handling for RAG agent with collection-specific parameters
            collection_key = list(self.collections.keys())[0]
            graph_params = (agent_config.llm, collection_key, self.persistance_db_path, self.collections[collection_key])

        return AgentMember(agent_config, state_class, graph_class(*graph_params))
