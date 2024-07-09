"""
Coder Graph
"""

from langgraph.graph import END
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph 
from langgraph.checkpoint.sqlite import SqliteSaver

from agents.coder.agent import CoderAgent
from agents.coder.state import CoderState

from configs.persistence_db import PERSISTANCE_DB_PATH

class CoderGraph:
    """
    """

    state: CoderState
    agent: CoderAgent
    memory: SqliteSaver
    app: CompiledGraph

    def __init__(self, llm) -> None:

        self.state = CoderState()
        self.agent = CoderAgent(llm)
        self.memory = SqliteSaver.from_conn_string(PERSISTANCE_DB_PATH)
        self.app = self.define_graph()
    
    def define_graph(self) -> CompiledGraph:

        coder_flow = StateGraph(CoderState)

        # node
        coder_flow.add_node(self.agent.entry_node_name, self.agent.entry_node)
        coder_flow.add_node(self.agent.code_generation_node_name, self.agent.code_generation_node)
        coder_flow.add_node(self.agent.download_license_node_name, self.agent.download_license_node)
        coder_flow.add_node(self.agent.add_license_node_name, self.agent.add_license_text_node)
        coder_flow.add_node(self.agent.update_state_node_name, self.agent.update_state)

        # edges
        coder_flow.add_conditional_edges(
            self.agent.entry_node_name,
            self.agent.router,
            {
                self.agent.code_generation_node_name: self.agent.code_generation_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name
            }
        )

        coder_flow.add_conditional_edges(
            self.agent.code_generation_node_name,
            self.agent.router,
            {
                self.agent.code_generation_node_name: self.agent.code_generation_node_name,
                self.agent.download_license_node_name: self.agent.download_license_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name
            }
        )

        coder_flow.add_conditional_edges(
            self.agent.download_license_node_name,
            self.agent.router,
            {
                self.agent.add_license_node_name: self.agent.add_license_node_name,
                self.agent.download_license_node_name: self.agent.download_license_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name
            }
        )

        coder_flow.add_conditional_edges(
            self.agent.add_license_node_name,
            self.agent.router,
            {
                self.agent.add_license_node_name: self.agent.add_license_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name
            }
        )

        coder_flow.add_edge(self.agent.update_state_node_name, END)

        # entry point
        coder_flow.set_entry_point(self.agent.entry_node_name)

        return coder_flow.compile(checkpointer=self.memory)
    

    def get_current_state(self) -> CoderState:
        """
        returns the current state of the graph.
        """
        
        return self.agent.state
    