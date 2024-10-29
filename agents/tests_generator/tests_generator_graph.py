"""TestCoder Graph"""

from langgraph.graph import END, StateGraph

from agents.agent.graph import Graph
from agents.tests_generator.tests_generator_agent import TestCoderAgent
from agents.tests_generator.tests_generator_state import TestCoderState
from llms.llm import LLM


class TestCoderGraph(Graph[TestCoderAgent]):
    """
    """

    def __init__(
            self,
            graph_id: str,
            graph_name: str,
            agent_id: str,
            agent_name: str,
            llm: LLM,
            persistance_db_path: str
        ) -> None:
        """
        """

        super().__init__(
            graph_id,
            graph_name,
            TestCoderAgent(agent_id, agent_name, llm),
            persistance_db_path
        )

        self.compile_graph_with_persistence()

    def define_graph(self) -> StateGraph:

        unit_test_coder_flow = StateGraph(TestCoderState)

        # node
        unit_test_coder_flow.add_node(
            self.agent.entry_node_name,
            self.agent.entry_node
        )
        unit_test_coder_flow.add_node(
            self.agent.skeleton_generation_node_name,
            self.agent.skeleton_generation_node
        )
        unit_test_coder_flow.add_node(
            self.agent.test_code_generation_node_name,
            self.agent.test_code_generation_node
        )
        unit_test_coder_flow.add_node(
            self.agent.skeleton_updation_node_name,
            self.agent.skeleton_updation_node
        )
        unit_test_coder_flow.add_node(
            self.agent.test_code_updation_node_name,
            self.agent.test_code_updation_node
        )
        unit_test_coder_flow.add_node(
            self.agent.write_skeleton_node_name,
            self.agent.write_skeleton_node
        )
        unit_test_coder_flow.add_node(
            self.agent.write_generated_code_node_name,
            self.agent.write_code_node
        )
        unit_test_coder_flow.add_node(
            self.agent.update_state_node_name, 
            self.agent.update_state
        )

        # edges
        unit_test_coder_flow.add_conditional_edges(
            self.agent.entry_node_name,
            self.agent.router,
            {
                self.agent.skeleton_generation_node_name:
                    self.agent.skeleton_generation_node_name,
                self.agent.skeleton_updation_node_name:
                    self.agent.skeleton_updation_node_name,
            }
        )

        unit_test_coder_flow.add_edge(
            self.agent.skeleton_generation_node_name,
            self.agent.write_skeleton_node_name
        )
        unit_test_coder_flow.add_edge(
            self.agent.skeleton_updation_node_name,
            self.agent.write_skeleton_node_name
        )

        unit_test_coder_flow.add_conditional_edges(
            self.agent.write_skeleton_node_name,
            self.agent.router,
            {
                self.agent.test_code_generation_node_name: 
                    self.agent.test_code_generation_node_name,
                self.agent.test_code_updation_node_name: 
                    self.agent.test_code_updation_node_name
            }
        )

        unit_test_coder_flow.add_edge(
            self.agent.test_code_generation_node_name,
            self.agent.write_generated_code_node_name
        )
        unit_test_coder_flow.add_edge(
            self.agent.test_code_updation_node_name,
            self.agent.write_generated_code_node_name
        )
        unit_test_coder_flow.add_edge(
            self.agent.write_generated_code_node_name,
            self.agent.update_state_node_name
        )
        unit_test_coder_flow.add_edge(
            self.agent.update_state_node_name,
            END
        )

        # entry point
        unit_test_coder_flow.set_entry_point(self.agent.entry_node_name)

        return unit_test_coder_flow

    def get_current_state(self) -> TestCoderState:
        """
        Method to fetch the current state of the graph.

        Returns:
            ArchitectState: The current state of the Architect agent.
        """
     
        return self.agent.state
