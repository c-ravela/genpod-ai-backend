"""
Coder Graph
"""
from langgraph.graph import END, StateGraph
from langgraph.graph.graph import CompiledGraph

from agents.base.base_graph import BaseGraph
from agents.coder.coder_agent import CoderAgent
from agents.coder.coder_state import CoderState
from llms.llm import LLM
from utils.logs.logging_utils import logger


class CoderGraph(BaseGraph[CoderAgent]):
    """
    CoderGraph Class

    Defines and manages the state graph for the CoderAgent, handling code generation,
    issue resolution, and related workflows.
    """

    def __init__(self, graph_id: str, graph_name: str, agent_id: str, agent_name: str, llm: LLM, persistance_db_path: str) -> None:
        """
        Initializes the CoderGraph with the specified parameters.

        Args:
            graph_id (str): Unique identifier for the graph.
            graph_name (str): Name of the graph.
            agent_id (str): Unique identifier for the associated agent.
            agent_name (str): Name of the associated agent.
            llm (LLM): Language learning model used by the agent.
            persistance_db_path (str): Path to the persistence database for state saving.
        """
        logger.info(f"Initializing CoderGraph with ID: {graph_id} and Name: {graph_name}")
        super().__init__(
            graph_id,
            graph_name, 
            CoderAgent(agent_id, agent_name, llm),
            persistance_db_path
        )

        self.compile_graph_with_persistence()
        logger.info(f"CoderGraph {graph_name} initialized and compiled successfully.")

    def define_graph(self) -> CompiledGraph:
        """
        Defines the state graph for the CoderAgent.

        Returns:
            CompiledGraph: The compiled state graph for the agent.
        """
        logger.info(f"Defining the state graph for CoderAgent.")
        coder_flow = StateGraph(CoderState)

        # node
        logger.debug("Adding nodes to the state graph.")
        coder_flow.add_node(self.agent.entry_node_name, self.agent.entry_node)
        coder_flow.add_node(self.agent.code_generation_node_name, self.agent.code_generation_node)
        coder_flow.add_node(self.agent.general_task_node_name, self.agent.general_task_node)
        coder_flow.add_node(self.agent.resolve_issue_node_name, self.agent.resolve_issue_node)
        # coder_flow.add_node(self.agent.run_commands_node_name, self.agent.run_commands_node)
        coder_flow.add_node(self.agent.write_generated_code_node_name, self.agent.write_code_node)
        coder_flow.add_node(self.agent.add_license_node_name, self.agent.add_license_text_node)
        coder_flow.add_node(self.agent.download_license_node_name, self.agent.download_license_node)
        coder_flow.add_node(self.agent.agent_response_node_name, self.agent.agent_response_node)
        coder_flow.add_node(self.agent.update_state_node_name, self.agent.update_state)

        # edges
        logger.debug("Adding conditional edges to the state graph.")
        coder_flow.add_conditional_edges(
            self.agent.entry_node_name,
            self.agent.router,
            {
                self.agent.code_generation_node_name: self.agent.code_generation_node_name,
                self.agent.general_task_node_name: self.agent.general_task_node_name,
                self.agent.resolve_issue_node_name: self.agent.resolve_issue_node_name
            }
        )

        logger.debug("Adding direct edges to the state graph.")
        coder_flow.add_edge(self.agent.general_task_node_name, self.agent.write_generated_code_node_name)
        coder_flow.add_edge(self.agent.resolve_issue_node_name, self.agent.write_generated_code_node_name)
        coder_flow.add_edge(self.agent.code_generation_node_name, self.agent.write_generated_code_node_name)
        coder_flow.add_edge(self.agent.write_generated_code_node_name, self.agent.add_license_node_name)

        # coder_flow.add_conditional_edges(
        #     self.agent.run_commands_node_name,
        #     self.agent.router,
        #     {
        #         self.agent.run_commands_node_name: self.agent.run_commands_node_name,
        #         self.agent.write_generated_code_node_name: self.agent.write_generated_code_node_name,
        #     }
        # )

        coder_flow.add_conditional_edges(
            self.agent.add_license_node_name,
            self.agent.router,
            {
                self.agent.download_license_node_name: self.agent.download_license_node_name,
                self.agent.agent_response_node_name: self.agent.agent_response_node_name
            }
        )

        coder_flow.add_edge(self.agent.download_license_node_name, self.agent.agent_response_node_name)
        coder_flow.add_edge(self.agent.agent_response_node_name, self.agent.update_state_node_name)
        coder_flow.add_edge(self.agent.update_state_node_name, END)

        # entry point
        logger.debug(f"Setting entry point to {self.agent.entry_node_name}.")
        coder_flow.set_entry_point(self.agent.entry_node_name)

        logger.info(f"State graph for CoderAgent defined successfully.")
        return coder_flow
    
    def get_current_state(self) -> CoderState:
        """
        Fetches the current state of the graph.

        Returns:
            CoderState: The current state of the agent.
        """
        logger.info(f"Fetching the current state of the CoderGraph.")
        return self.agent.state
