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

    def __init__(self, llm) -> None:

        self.state: CoderState = CoderState()
        self.agent: CoderAgent = CoderAgent(llm)
        self.memory: SqliteSaver = SqliteSaver.from_conn_string(PERSISTANCE_DB_PATH)
        self.app = self.define_graph()
    

    def define_graph(self) -> CompiledGraph:

        coder_flow = StateGraph(CoderState)

        # node
        coder_flow.add_node(self.agent.code_generation, self.agent.code_generation_node)
        coder_flow.add_node(self.agent.execute_tools, self.agent.execute_tools_node)
        coder_flow.add_node(self.agent.state_update, self.agent.update_state)

        # edges
        coder_flow.add_conditional_edges(
            self.agent.code_generation,
            self.agent.router,
            {
                self.agent.code_generation: self.agent.code_generation,
                self.agent.execute_tools: self.agent.execute_tools,
                self.agent.state_update:self.agent.state_update
            }
        )

        coder_flow.add_conditional_edges(
            self.agent.execute_tools,
            self.agent.router,
            {
                self.agent.code_generation: self.agent.code_generation,
                self.agent.execute_tools: self.agent.execute_tools,
                self.agent.state_update:self.agent.state_update
            }
        )

        coder_flow.add_edge(self.agent.state_update, END)

        # entry point
        coder_flow.set_entry_point(self.agent.code_generation)

        return coder_flow.compile(checkpointer=self.memory)
    

    def get_current_state(self) -> CoderState:
        """
        returns the current state of the graph.
        """
        
        return self.agent.state
    