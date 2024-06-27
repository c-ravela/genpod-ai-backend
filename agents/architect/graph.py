"""Architect Graph

This module contains the Architect class which is responsible for defining
the state graph for the Architect agent. The state graph determines the flow 
of control between different states of the Architect agent.
"""

from langgraph.graph import END
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph 
from langgraph.checkpoint.sqlite import SqliteSaver

from agents.architect.agent import ArchitectAgent
from agents.architect.state import ArchitectState

from configs.persistence_db import PERSISTANCE_DB_PATH

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
        
        self.state: ArchitectState = {}
        self.agent = ArchitectAgent(llm)
        self.memory: SqliteSaver = SqliteSaver.from_conn_string(PERSISTANCE_DB_PATH)
        self.app: CompiledGraph = self.define_graph()

    def define_graph(self) -> CompiledGraph:
        """
        Defines the state graph for the Architect agent. The graph includes 
        nodes representing different states of the agent and edges 
        representing possible transitions between states. The method returns 
        the compiled state graph.

        Returns:
            CompiledGraph: The compiled state graph for the Architect agent.
        """

        architect_flow = StateGraph(ArchitectState)

        # node
        architect_flow.add_node(self.agent.requirements_and_additional_context, self.agent.requirements_and_additional_context_node)
        architect_flow.add_node(self.agent.write_requirements, self.agent.write_requirements_to_local_node)
        architect_flow.add_node(self.agent.tasks_seperation, self.agent.tasks_seperation_node)

        # edges
        architect_flow.add_conditional_edges(
            self.agent.requirements_and_additional_context,
            self.agent.router, 
            {
                self.agent.requirements_and_additional_context: self.agent.requirements_and_additional_context,
                self.agent.tasks_seperation: self.agent.tasks_seperation,
                self.agent.write_requirements:self.agent.write_requirements,
                END:END
            }
        )

        architect_flow.add_conditional_edges(
            self.agent.tasks_seperation,
            self.agent.router, 
            {
                self.agent.requirements_and_additional_context: self.agent.requirements_and_additional_context,
                self.agent.tasks_seperation: self.agent.tasks_seperation,
                self.agent.write_requirements:self.agent.write_requirements,
                END:END
            }
        )

        architect_flow.add_conditional_edges(
            self.agent.write_requirements,
            self.agent.router, 
            {
                self.agent.requirements_and_additional_context: self.agent.requirements_and_additional_context,
                self.agent.tasks_seperation: self.agent.tasks_seperation,
                self.agent.write_requirements:self.agent.write_requirements,
                END:END
            }
        )
        # entry point
        architect_flow.set_entry_point(self.agent.requirements_and_additional_context)

        return architect_flow.compile(checkpointer=self.memory)

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