"""TestCoder Graph"""

from langgraph.graph import END, StateGraph

from agents.base.base_graph import BaseGraph
from agents.tests_generator.tests_generator_agent import TestCoderAgent
from agents.tests_generator.tests_generator_state import TestCoderState
from llms.llm import LLM
from utils.logs.logging_utils import logger


class TestCoderGraph(BaseGraph[TestCoderAgent]):
    """
    Defines the workflow for the TestCoder agent, managing the flow of tasks
    such as skeleton generation, test code generation, and writing test code.
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
        Initializes the TestCoderGraph and compiles it with persistence.

        Args:
            graph_id (str): Unique identifier for the graph.
            graph_name (str): Descriptive name of the graph.
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Descriptive name of the agent.
            llm (LLM): The language model used by the agent.
            persistance_db_path (str): Path for persisting graph state.
        """
        logger.info(f"Initializing TestCoderGraph with ID: {graph_id}, Name: {graph_name}")
        super().__init__(
            graph_id,
            graph_name,
            TestCoderAgent(agent_id, agent_name, llm),
            persistance_db_path
        )

        self.compile_graph_with_persistence()
        logger.info("TestCoderGraph compiled with persistence successfully.")

    def define_graph(self) -> StateGraph:
        """
        Defines the state graph for the TestCoder agent.

        Returns:
            StateGraph: Configured state graph for the agent.
        """
        logger.info("Defining the TestCoderGraph workflow...")
        unit_test_coder_flow = StateGraph(TestCoderState)

        # node
        logger.debug("Adding nodes to the graph...")
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
        logger.debug("Adding edges between nodes...")
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
        logger.debug("Setting the entry point for the graph.")
        unit_test_coder_flow.set_entry_point(self.agent.entry_node_name)

        logger.info("TestCoderGraph workflow defined successfully.")
        return unit_test_coder_flow

    def get_current_state(self) -> TestCoderState:
        """
        Fetches the current state of the TestCoder agent.

        Returns:
            TestCoderState: Current state of the TestCoder agent.
        """
        logger.info("Fetching the current state of the TestCoder agent.")
        return self.agent.state
