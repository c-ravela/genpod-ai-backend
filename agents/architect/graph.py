"""Architect Graph

This module contains the Architect class which is responsible for defining
the state graph for the Architect agent. The state graph determines the flow 
of control between different states of the Architect agent.
"""

from langgraph.graph import END
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph 

from agents.architect.agent import ArchitectAgent
from agents.architect.state import ArchitectState

class ArchitectGraph:
    """
    ArchitectGraph Class

    This class defines the state graph for the Architect agent. The state 
    graph is used to manage the flow of control between different states of 
    the Architect agent. It includes methods to define the graph, add nodes 
    and edges, and set the entry point.
    """
    
    def __init__(self, llm) -> None:
        """
        Initializes the Architect with a given Language Learning Model (llm) 
        and defines the state graph.
        """
               
        self.agent = ArchitectAgent(llm)
        self.app = self.define_graph()
        self.state = {}

    def define_graph(self) -> CompiledGraph:
        """
        Defines the state graph for the Architect agent. The graph includes 
        nodes representing different states of the agent and edges 
        representing possible transitions between states. The method returns 
        the compiled state graph.
        """

        architect_flow = StateGraph(ArchitectState)

        # node
        architect_flow.add_node(self.agent.name, self.agent.node)

        # edges
        architect_flow.add_conditional_edges(
            self.agent.name,
            self.agent.router, 
            {
                self.agent.name: self.agent.name,
                END:END
            }
        )

        # entry point
        architect_flow.set_entry_point(self.agent.name)

        return architect_flow.compile()

    def update_state(self, state: any) -> any:
        """
        The method takes in a state, updates the current state of the object with the 
        provided state, and then returns the updated state.

        Args:
            state (any): The state to update the current state of the object with.

        Returns:
            any: The updated state of the object.
        """
        
        self.state.update(state)

        return {**self.state}