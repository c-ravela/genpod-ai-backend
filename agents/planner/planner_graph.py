from langgraph.graph import END, StateGraph

from agents.base.base_graph import BaseGraph
from agents.planner.planner_agent import PlannerAgent
from agents.planner.planner_state import PlannerState
from llms.llm import LLM
from models.models import Task
from utils.logs.logging_utils import logger


class PlannerWorkFlow(BaseGraph[PlannerAgent]):
    """
    PlannerWorkFlow defines and manages the state graph for the PlannerAgent.
    """

    def __init__(
        self,
        graph_id: str,
        graph_name: str,
        agent_id: str,
        agent_name: str,
        llm: LLM,
        persistance_db_path: str
    ):
        """
        Initializes the PlannerWorkFlow with the given parameters.

        Args:
            graph_id (str): Unique identifier for the graph.
            graph_name (str): Name of the graph.
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Name of the agent.
            llm (LLM): Instance of the language model.
            persistance_db_path (str): Path for persistence database.
        """
        super().__init__(
            graph_id,
            graph_name, 
            PlannerAgent(agent_id, agent_name, llm),
            persistance_db_path
        )
        logger.info(f"Initializing PlannerWorkFlow with graph ID: {graph_id} and agent: {agent_name}.")
        self.compile_graph_with_persistence()

    def define_graph(self) -> StateGraph:
        """
        Defines the state graph for the PlannerAgent workflow.

        Returns:
            StateGraph: The defined state graph.
        """
        logger.info("Defining the state graph for PlannerWorkFlow.")
        planner_workflow = StateGraph(PlannerState, config_schema=Task)
        
        # Define the nodes
        logger.info("Adding nodes to the graph.")
        planner_workflow.add_node(self.agent.task_breakdown_node_name, self.agent.task_breakdown_node)
        planner_workflow.add_node(self.agent.requirements_analyzer_node_name, self.agent.requirements_analyzer_node)
        planner_workflow.add_node(self.agent.issues_preparation_node_name, self.agent.issues_preparation_node)
        planner_workflow.add_node(self.agent.agent_response_node_name, self.agent.agent_response_node)
        planner_workflow.add_node(self.agent.update_state_node_name, self.agent.update_state)

        # Define edges
        logger.info("Adding edges to define transitions between nodes.")
        planner_workflow.add_edge(self.agent.task_breakdown_node_name, self.agent.requirements_analyzer_node_name)
        planner_workflow.add_edge(self.agent.requirements_analyzer_node_name, self.agent.agent_response_node_name)
        planner_workflow.add_edge(self.agent.issues_preparation_node_name, self.agent.agent_response_node_name)
        planner_workflow.add_edge(self.agent.agent_response_node_name, self.agent.update_state_node_name)
        planner_workflow.add_edge(self.agent.update_state_node_name, END)

        # Define entry point
        logger.info("Setting conditional entry point for the graph.")
        planner_workflow.set_conditional_entry_point(
            self.agent.new_deliverable_check,
            {
                self.agent.task_breakdown_node_name: self.agent.task_breakdown_node_name,
                self.agent.requirements_analyzer_node_name: self.agent.requirements_analyzer_node_name,
                self.agent.issues_preparation_node_name: self.agent.issues_preparation_node_name
            }
        )

        logger.info("State graph definition completed.")
        return planner_workflow

    def get_current_state(self):
        """
        Retrieves the current state of the PlannerAgent.

        Returns:
            dict: Current state dictionary of the agent.
        """
        logger.info(f"Retrieving the current state of the agent: {self.agent.agent_name}.")
        return self.agent.state
