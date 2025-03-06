from langgraph.graph import StateGraph

from agents.supervisor._internal.supervisor_state import (SupervisorInput,
                                                          SupervisorOuptut,
                                                          SupervisorState)
from agents.supervisor._internal.supervisor_work_flow import SupervisorWorkFlow
from core.graph import BaseGraph
from utils.logs.logging_utils import logger


class SupervisorGraph(BaseGraph[SupervisorWorkFlow]):
    """
    SupervisorGraph sets up and defines the workflow graph for the supervisor, including nodes and edges.
    
    Attributes:
        work_flow (SupervisorWorkFlow): The workflow instance containing logic for supervisor operations.
        recursion_limit (int): The recursion limit for graph processing.
        persistence_db_path (str): Path to the persistence database.
    """

    def __init__(self, work_flow: SupervisorWorkFlow, recursion_limit: int, persistence_db_path: str):
        """
        Initialize a SupervisorGraph instance.

        Args:
            work_flow (SupervisorWorkFlow): The workflow instance for the supervisor.
            recursion_limit (int): The recursion limit for graph execution.
            persistence_db_path (str): The file path to the persistence database.
        """
        super().__init__(work_flow, recursion_limit, persistence_db_path)

    def define_graph(self) -> StateGraph:
        """
        Define and configure the state graph for the supervisor workflow.

        Returns:
            StateGraph: A fully defined state graph for the supervisor workflow.
        """
        state_graph = StateGraph(SupervisorState, input=SupervisorInput, output=SupervisorOuptut)
        team = self.work_flow.team

        node_mapping = {
            'entry': self.work_flow.entry_node,
            'call_supervisor': self.work_flow.call_supervisor,
            'call_architect': self.work_flow.call_architect,
            'call_planner': self.work_flow.call_planner,
            'call_coder': self.work_flow.call_coder,
            'call_test_code_generator': self.work_flow.call_test_code_generator,
            'call_reviewer': self.work_flow.call_reviewer,
            'human': self.work_flow.call_human,
            'exit': self.work_flow.exit_node,
        }

        edge_mapping = {
            'call_supervisor': 'call_supervisor',
            'call_architect': 'call_architect',
            'call_planner': 'call_planner',
            'call_coder': 'call_coder',
            'call_test_code_generator': 'call_test_code_generator',
            'call_reviewer': 'call_reviewer',
            'human': 'human',
            'exit': 'exit'
        }

        for node_name, node_function in node_mapping.items():
            state_graph.add_node(node_name, node_function)
            logger.debug("Added node '%s' with associated function '%s'", node_name, node_function.__name__)

        supervisor_id = 'call_supervisor'
        state_graph.add_edge('entry', supervisor_id)
        state_graph.add_edge('human', supervisor_id)
        state_graph.add_edge('call_architect', supervisor_id)
        state_graph.add_edge('call_planner', supervisor_id)
        state_graph.add_edge('call_coder', supervisor_id)
        state_graph.add_edge('call_test_code_generator', supervisor_id)
        state_graph.add_edge('call_reviewer', supervisor_id)

        state_graph.add_conditional_edges(supervisor_id, self.work_flow.router, edge_mapping)
        logger.debug("Added conditional edges for node '%s' using router '%s'", supervisor_id, self.work_flow.router.__name__)

        state_graph.set_entry_point('entry')
        state_graph.set_finish_point('exit')
        logger.info("Graph defined with entry point 'entry' and finish point 'exit'")

        return state_graph
