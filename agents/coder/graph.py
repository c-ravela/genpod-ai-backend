"""
Coder Graph
"""

from langgraph.graph import END
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph 

from agents import architect
from agents.coder.agent import CoderAgent
from agents.coder.state import CoderState


class Coder:
    """
    """

    def __init__(self, llm) -> None:
        self.agent = CoderAgent(llm)
        self.app = self.define_graph()
    

    def define_graph(self) -> CompiledGraph:

        coder_flow = StateGraph(CoderState)

        # node
        coder_flow.add_node(self.agent.name, self.agent.node)

        coder_flow.add_conditional_edges(
            self.agent.name,
            self.agent.router,
            {
                self.agent.name: self.agent.name,
                END: END
            }
        )

        coder_flow.set_entry_point(self.agent.name)
        return coder_flow.compile()