"""
TestCoder Graph
"""

from langgraph.graph import END
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph 
from langgraph.checkpoint.sqlite import SqliteSaver

from agents.tester.agent import TestCoderAgent
from agents.tester.state import TestCoderState

from configs.persistence_db import PERSISTANCE_DB_PATH

class TestCoderGraph:
    """
    """

    state: TestCoderState
    agent: TestCoderAgent
    memory: SqliteSaver
    app: CompiledGraph

    def __init__(self, llm) -> None:

        self.state = TestCoderState()
        self.agent = TestCoderAgent(llm)
        # self.memory = SqliteSaver.from_conn_string(PERSISTANCE_DB_PATH)
        self.app = self.define_graph()
    
    def define_graph(self) -> CompiledGraph:

        unit_test_coder_flow = StateGraph(TestCoderState)

        # node
        unit_test_coder_flow.add_node(self.agent.entry_node_name, self.agent.entry_node)
        unit_test_coder_flow.add_node(self.agent.skeleton_generation_node_name,self.agent.skeleton_generation_node)
        unit_test_coder_flow.add_node(self.agent.test_code_generation_node_name, self.agent.test_code_generation_node)
        unit_test_coder_flow.add_node(self.agent.run_commands_node_name, self.agent.run_commands_node)
        unit_test_coder_flow.add_node(self.agent.write_skeleton_node_name, self.agent.write_skeleton_node)
        unit_test_coder_flow.add_node(self.agent.write_generated_code_node_name, self.agent.write_code_node)
        unit_test_coder_flow.add_node(self.agent.update_state_node_name, self.agent.update_state)

        # edges
        unit_test_coder_flow.add_conditional_edges(
            self.agent.entry_node_name,
            self.agent.router,
            {
                self.agent.skeleton_generation_node_name: self.agent.skeleton_generation_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name
            }
        )

        unit_test_coder_flow.add_conditional_edges(
            self.agent.skeleton_generation_node_name,
            self.agent.router,{
                self.agent.skeleton_generation_node_name:self.agent.skeleton_generation_node_name,
                self.agent.write_skeleton_node_name: self.agent.write_skeleton_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name})
        
        unit_test_coder_flow.add_conditional_edges(
            self.agent.write_skeleton_node_name,
            self.agent.router,
            {
                self.agent.write_skeleton_node_name: self.agent.write_skeleton_node_name,
                self.agent.test_code_generation_node_name: self.agent.test_code_generation_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name
            }
        )


        unit_test_coder_flow.add_conditional_edges(
            self.agent.test_code_generation_node_name,
            self.agent.router,
            {
                self.agent.test_code_generation_node_name: self.agent.test_code_generation_node_name,
                self.agent.write_generated_code_node_name: self.agent.write_generated_code_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name
            }
        )

        unit_test_coder_flow.add_conditional_edges(
            self.agent.run_commands_node_name,
            self.agent.router,
            {
                self.agent.run_commands_node_name: self.agent.run_commands_node_name,
                self.agent.write_generated_code_node_name: self.agent.write_generated_code_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name
            }
        )

        unit_test_coder_flow.add_conditional_edges(
            self.agent.write_generated_code_node_name,
            self.agent.router,
            {
                self.agent.write_generated_code_node_name: self.agent.write_generated_code_node_name,
                self.agent.update_state_node_name:self.agent.update_state_node_name
            }
        )

        unit_test_coder_flow.add_edge(self.agent.update_state_node_name, END)

        # entry point
        unit_test_coder_flow.set_entry_point(self.agent.entry_node_name)

        return unit_test_coder_flow.compile()
    

    def get_current_state(self) -> TestCoderState:
        """
        returns the current state of the graph.
        """
        
        return self.agent.state
    