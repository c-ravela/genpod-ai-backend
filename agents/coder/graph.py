"""
Coder Graph
"""
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.graph import CompiledGraph
from typing_extensions import Union

from agents.agent.graph import Graph
from agents.coder.agent import CoderAgent
from agents.coder.state import CoderState
from configs.project_config import ProjectGraphs


class CoderGraph(Graph[CoderAgent]):
    """
    """

    def __init__(self,  llm: Union[ChatOpenAI, ChatOllama], persistance_db_path: str) -> None:
        """"""
        super().__init__(
            ProjectGraphs.coder.graph_id,
            ProjectGraphs.coder.graph_name, 
            CoderAgent(llm),
            persistance_db_path
        )

        self.compile_graph_with_persistence()
    
    def define_graph(self) -> CompiledGraph:

        coder_flow = StateGraph(CoderState)

        # node
        coder_flow.add_node(self.agent.entry_node_name, self.agent.entry_node)
        coder_flow.add_node(self.agent.code_generation_node_name, self.agent.code_generation_node)
        coder_flow.add_node(self.agent.run_commands_node_name, self.agent.run_commands_node)
        coder_flow.add_node(self.agent.write_generated_code_node_name, self.agent.write_code_node)
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
                self.agent.write_generated_code_node_name: self.agent.write_generated_code_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name,
                self.agent.add_license_node_name: self.agent.add_license_node_name,
            }
        )

        coder_flow.add_conditional_edges(
            self.agent.run_commands_node_name,
            self.agent.router,
            {
                self.agent.run_commands_node_name: self.agent.run_commands_node_name,
                self.agent.write_generated_code_node_name: self.agent.write_generated_code_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name
            }
        )

        coder_flow.add_conditional_edges(
            self.agent.write_generated_code_node_name,
            self.agent.router,
            {
                self.agent.write_generated_code_node_name: self.agent.write_generated_code_node_name,
                self.agent.download_license_node_name: self.agent.download_license_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name,
                self.agent.add_license_node_name: self.agent.add_license_node_name,
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

        return coder_flow
    
    def get_current_state(self) -> CoderState:
        """
        returns the current state of the graph.
        """
        
        return self.agent.state
    