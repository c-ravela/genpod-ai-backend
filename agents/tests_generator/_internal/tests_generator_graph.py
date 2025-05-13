"""TestCoder Graph"""

from langgraph.graph import END, StateGraph

from agents.tests_generator._internal.tests_generator_node_enum import \
    TestsGeneratorNodeEnum
from agents.tests_generator._internal.tests_generator_state import (
    TestCoderInput, TestCoderOutput, TestCoderState)
from agents.tests_generator._internal.tests_generator_work_flow import \
    TestCoderWorkFlow
from core.graph import BaseGraph
from utils.logger import logger


class TestCoderGraph(BaseGraph[TestCoderWorkFlow]):
    """
    Graph representation for the Test Coder workflow.

    This graph defines the state transitions for the Test Coder agent's workflow,
    including nodes for entry, skeleton generation/updation, test code generation/updation,
    writing generated code, and exit. The graph leverages the TestCoderWorkFlow to set up
    the nodes and transitions, enabling conditional routing based on the workflow's state.
    """
    def __init__(
        self,
        work_flow: TestCoderWorkFlow,
        recursion_limit: int,
        persistence_db_path: str
    ):
        """
        Initialize the TestCoderGraph.

        Args:
            work_flow (TestCoderWorkFlow): The workflow object containing node implementations.
            recursion_limit (int): The recursion limit for the graph processing.
            persistence_db_path (str): The path to the persistence database.
        """
        logger.debug(
            "Initializing TestCoderGraph with recursion_limit: %s and persistence_db_path: %s",
            recursion_limit, persistence_db_path
        )
        super().__init__(work_flow, recursion_limit, persistence_db_path)

    def define_graph(self) -> StateGraph:
        """
        Define the state graph for the Test Coder workflow.

        This method creates a StateGraph using TestCoderState for state management,
        TestCoderInput as the input schema, and TestCoderOutput as the output schema.
        It adds the workflow nodes (entry, skeleton generation/updation, test code generation/updation,
        code writing, and exit), configures the edges between nodes—including conditional edges
        determined by the workflow's router—and sets the entry and finish points.

        Returns:
            StateGraph: The fully defined state graph for the Test Coder workflow.
        """
        logger.debug("Defining the TestCoderGraph state graph.")
        tests_generator_work_flow = StateGraph(TestCoderState, input=TestCoderInput, output=TestCoderOutput)

        nodes = {
            TestsGeneratorNodeEnum.ENTRY: self.work_flow.entry_node,
            TestsGeneratorNodeEnum.SKELETON_GENERATION: self.work_flow.skeleton_generation_node,
            TestsGeneratorNodeEnum.SKELETON_UPDATION: self.work_flow.skeleton_updation_node,
            TestsGeneratorNodeEnum.WRITE_SKELETON: self.work_flow.write_skeleton_node,
            TestsGeneratorNodeEnum.TEST_CODE_GENERATION: self.work_flow.test_code_generation_node,
            TestsGeneratorNodeEnum.TEST_CODE_UPDATION: self.work_flow.test_code_updation_node,
            TestsGeneratorNodeEnum.WRITE_GENERATED_CODE: self.work_flow.write_generated_code_node,
            TestsGeneratorNodeEnum.EXIT: self.work_flow.exit_node
        }

        for node_name, node_function in nodes.items():
            tests_generator_work_flow.add_node(str(node_name), node_function)
            logger.debug("Added node: %s", node_name)

        tests_generator_work_flow.add_conditional_edges(
            str(TestsGeneratorNodeEnum.ENTRY),
            self.work_flow.router,
            {
                str(TestsGeneratorNodeEnum.SKELETON_GENERATION): str(TestsGeneratorNodeEnum.SKELETON_GENERATION),
                str(TestsGeneratorNodeEnum.SKELETON_UPDATION): str(TestsGeneratorNodeEnum.SKELETON_UPDATION)
            }
        )

        tests_generator_work_flow.add_edge(
            str(TestsGeneratorNodeEnum.SKELETON_GENERATION),
            str(TestsGeneratorNodeEnum.WRITE_SKELETON)
        )

        tests_generator_work_flow.add_edge(
            str(TestsGeneratorNodeEnum.SKELETON_UPDATION),
            str(TestsGeneratorNodeEnum.WRITE_SKELETON)
        )

        tests_generator_work_flow.add_conditional_edges(
            str(TestsGeneratorNodeEnum.WRITE_SKELETON),
            self.work_flow.router,
            {
                str(TestsGeneratorNodeEnum.TEST_CODE_GENERATION): str(TestsGeneratorNodeEnum.TEST_CODE_GENERATION),
                str(TestsGeneratorNodeEnum.TEST_CODE_UPDATION): str(TestsGeneratorNodeEnum.TEST_CODE_UPDATION)
            }
        )

        tests_generator_work_flow.add_edge(
            str(TestsGeneratorNodeEnum.TEST_CODE_GENERATION),
            str(TestsGeneratorNodeEnum.WRITE_GENERATED_CODE)
        )

        tests_generator_work_flow.add_edge(
            str(TestsGeneratorNodeEnum.TEST_CODE_UPDATION),
            str(TestsGeneratorNodeEnum.WRITE_GENERATED_CODE)
        )

        tests_generator_work_flow.add_edge(
            str(TestsGeneratorNodeEnum.WRITE_GENERATED_CODE),
            str(TestsGeneratorNodeEnum.EXIT)
        )

        tests_generator_work_flow.set_entry_point(str(TestsGeneratorNodeEnum.ENTRY))
        tests_generator_work_flow.set_finish_point(str(TestsGeneratorNodeEnum.EXIT))
        logger.debug("Set entry point to ENTRY and finish point to EXIT.")

        return tests_generator_work_flow
