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

    This class is responsible for defining and managing the state graph for the Architect agent. 
    The state graph is a control flow diagram that dictates the transitions between different states 
    of the Architect agent. This class provides methods to define the graph, add nodes and edges, 
    and designate the entry point.
    """

    state: ArchitectState
    agent: ArchitectAgent
    memory: SqliteSaver
    app: CompiledGraph

    def __init__(self, llm) -> None:
        """
        Constructor for the ArchitectGraph class.

        This method initializes the ArchitectGraph with a specified Language Learning Model (llm) 
        and sets up the state graph.
        """
        
        self.state = ArchitectState()
        self.agent = ArchitectAgent(llm)
        self.memory = SqliteSaver.from_conn_string(PERSISTANCE_DB_PATH)
        self.app = self.define_graph()

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
        architect_flow.add_node(self.agent.entry_node_name, self.agent.entry_node)
        architect_flow.add_node(self.agent.requirements_node_name, self.agent.requirements_node)
        architect_flow.add_node(self.agent.additional_info_node_name, self.agent.additional_information_node)
        architect_flow.add_node(self.agent.write_requirements_node_name, self.agent.write_requirements_node)
        architect_flow.add_node(self.agent.tasks_separation_node_name, self.agent.tasks_separation_node)
        architect_flow.add_node(self.agent.project_details_node_name, self.agent.project_details_node)
        architect_flow.add_node(self.agent.update_state_node_name, self.agent.update_state)

        # edges
        architect_flow.add_conditional_edges(
            self.agent.entry_node_name,
            self.agent.router, 
            {
                self.agent.requirements_node_name: self.agent.requirements_node_name,
                self.agent.additional_info_node_name: self.agent.additional_info_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name,
            }
        )
        
        architect_flow.add_conditional_edges(
            self.agent.requirements_node_name,
            self.agent.router,
            {
                self.agent.requirements_node_name: self.agent.requirements_node_name,
                self.agent.write_requirements_node_name: self.agent.write_requirements_node_name,
                self.agent.tasks_separation_node_name: self.agent.tasks_separation_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        architect_flow.add_conditional_edges(
            self.agent.additional_info_node_name,
            self.agent.router,
            {   
                self.agent.additional_info_node_name: self.agent.additional_info_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        architect_flow.add_conditional_edges(
            self.agent.write_requirements_node_name,
            self.agent.router, 
            {
                self.agent.tasks_separation_node_name: self.agent.tasks_separation_node_name,
                self.agent.requirements_node_name:self.agent.requirements_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        architect_flow.add_conditional_edges(
            self.agent.tasks_separation_node_name,
            self.agent.router, 
            {
                self.agent.tasks_separation_node_name: self.agent.tasks_separation_node_name,
                self.agent.project_details_node_name: self.agent.project_details_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        architect_flow.add_conditional_edges(
            self.agent.project_details_node_name,
            self.agent.router, 
            {
                self.agent.project_details_node_name: self.agent.project_details_node_name,
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        architect_flow.add_edge(self.agent.update_state_node_name, END)

        # entry point
        architect_flow.set_entry_point(self.agent.entry_node_name)

        return architect_flow.compile(checkpointer=self.memory)

    def get_current_state(self) -> ArchitectState:
        """
        Method to fetch the current state of the graph.

        Returns:
            ArchitectState: The current state of the Architect agent.
        """
        
        return self.agent.current_state