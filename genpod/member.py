from enum import Enum
from typing import Any, Dict, Generic, Iterator, TypeVar

from langchain_openai import ChatOpenAI

from agents.agent.graph import Graph
from agents.agent.state import State
from configs.project_config import AgentInfo

GenericAgentState = TypeVar('GenericAgentState', bound=Any)
GenericAgentGraph = TypeVar('GenericAgentGraph', bound=Graph)

class AgentMember(Generic[GenericAgentState, GenericAgentGraph]):
    """
    Represents an individual agent with its configuration and state.
    """

    class Role(Enum):
        MANAGER = 'manager'
        LEAD = 'lead'
        MEMBER = 'member'

    member_id: str
    member_name: str
    member_role: Role

    llm: ChatOpenAI
    thread_id: int
    fields: list[str]
    in_fields: list[str]
    out_fields: list[str]
    inout_fields: list[str]
    graph: GenericAgentGraph
    
    recursion_limit: int

    def __init__(self, agent_info: AgentInfo, state_class: GenericAgentState, graph: GenericAgentGraph) -> None:
        """
        Initializes an AgentMember instance with the given configuration and state.
        """
        self.member_id = agent_info.agent_id
        self.member_name = agent_info.agent_name
        self.llm = agent_info.llm
        self.thread_id = agent_info.thread_id

        sc = State(state_class)
        self.fields = sc.get_fields()
        self.in_fields = sc.get_in_fields()
        self.out_fields = sc.get_out_fields()
        self.inout_fields = sc.get_inout_fields()

        self.graph = graph
        self.recursion_limit = -1 # means no limit set
        self.member_role: self.Role = self.Role.MEMBER  # Default role

    def stream(self, input: Dict[str, Any] | Any) -> Iterator[Dict[str, GenericAgentState]]:
        return self._invoke_graph('stream', input)

    def invoke(self, input: Dict[str, Any] | Any) -> GenericAgentState:
        return self._invoke_graph('invoke', input)
    
    def get_last_saved_state(self) -> Dict[str, Any]:
        """
        Retrieves the last saved state of the agent using the thread ID.

        Returns:
            Dict[str, Any]: The saved state of the agent as retrieved from the graph's application.

        Raises:
            ValueError: If no state is found for the given thread ID.
        """
        graph_config = {"configurable": {"thread_id": self.thread_id}}
        return self.graph.app.get_state(graph_config).values

    def _invoke_graph(self, method_name: str, input: Dict[str, Any] | Any) -> Any:
        graph_config = {"configurable": {"thread_id": self.thread_id}}
        if self.recursion_limit != -1:
            graph_config['recursion_limit'] = self.recursion_limit
        
        return getattr(self.graph.app, method_name)(input, graph_config)

    def set_recursion_limit(self, limit: int) -> None:
        """
        """

        self.recursion_limit = limit

    def set_role(self, role: Role) -> None:
        self.member_role = role

    def __str__(self) -> str:
        return (f"AgentMember(member_id={self.member_id!r}, "
                f"member_name={self.member_name!r}, "
                f"member_role={self.member_role!r}, "
                f"llm_type={type(self.llm).__name__}, "
                f"thread_id={self.thread_id}, "
                f"fields={self.fields}, "
                f"in_fields={self.in_fields}, "
                f"out_fields={self.out_fields}, "
                f"inout_fields={self.inout_fields}, "
                f"graph_type={type(self.graph).__name__}, "
                f"recursion_limit={self.recursion_limit})")
