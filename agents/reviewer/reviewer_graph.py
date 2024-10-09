"""
"""
from langgraph.graph import END, StateGraph

from agents.agent.graph import Graph
from agents.reviewer.reviewer_agent import ReviewerAgent
from agents.reviewer.reviewer_state import ReviewerState
from llms.llm import LLM


class ReviewerGraph(Graph[ReviewerAgent]):
    """
    """

    def __init__(self, graph_id: str, graph_name: str, agent_id: str, agent_name: str, llm: LLM, persistance_db_path: str) -> None:
        """"""
        super().__init__(
            graph_id,
            graph_name, 
            ReviewerAgent(agent_id, agent_name, llm),
            persistance_db_path
        )

        self.compile_graph_with_persistence()

    def define_graph(self) -> StateGraph:
        
        reviewer_flow = StateGraph(ReviewerState)

        # nodes
        reviewer_flow.add_node(self.agent.entry_node_name, self.agent.entry_node)
        reviewer_flow.add_node(self.agent.static_code_analysis_node_name, self.agent.static_code_analysis_node)
        reviewer_flow.add_node(self.agent.update_state_node_name, self.agent.update_state)
        
        # edges
        reviewer_flow.add_edge(self.agent.entry_node_name, self.agent.static_code_analysis_node_name)
        
        reviewer_flow.add_conditional_edges(
            self.agent.static_code_analysis_node_name,
            self.agent.router,
            {
                self.agent.update_state_node_name: self.agent.update_state_node_name
            }
        )

        reviewer_flow.add_edge(self.agent.update_state_node_name, END)

        # entry point
        reviewer_flow.set_entry_point(self.agent.entry_node_name)

        return reviewer_flow
        
    
    def get_current_state(self) -> ReviewerState:
        """
        returns the current state of the graph.
        """
        
        return self.agent.state
    