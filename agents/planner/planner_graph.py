from langgraph.graph import END, StateGraph

from agents.base.base_graph import BaseGraph
from agents.planner.planner_agent import PlannerAgent
from agents.planner.planner_state import PlannerState
from llms.llm import LLM
from models.models import Task


class PlannerWorkFlow(BaseGraph[PlannerAgent]):
    def __init__(self, graph_id: str, graph_name: str, agent_id: str, agent_name: str, llm: LLM, persistance_db_path: str):
        super().__init__(
            graph_id,
            graph_name, 
            PlannerAgent(agent_id, agent_name, llm),
            persistance_db_path
        )

        self.compile_graph_with_persistence()

    def define_graph(self) -> StateGraph:
        
        planner_workflow = StateGraph(PlannerState, config_schema=Task)
        
        # Define the nodes
        planner_workflow.add_node(self.agent.task_breakdown_node_name, self.agent.task_breakdown_node)
        planner_workflow.add_node(self.agent.requirements_analyzer_node_name, self.agent.requirements_analyzer_node)
        planner_workflow.add_node(self.agent.issues_preparation_node_name, self.agent.issues_preparation_node)
        planner_workflow.add_node(self.agent.agent_response_node_name, self.agent.agent_response_node)
        planner_workflow.add_node(self.agent.update_state_node_name, self.agent.update_state)

        # Define edges
        planner_workflow.add_edge(self.agent.task_breakdown_node_name, self.agent.requirements_analyzer_node_name)
        planner_workflow.add_edge(self.agent.requirements_analyzer_node_name, self.agent.agent_response_node_name)
        planner_workflow.add_edge(self.agent.issues_preparation_node_name, self.agent.agent_response_node_name)
        planner_workflow.add_edge(self.agent.agent_response_node_name, self.agent.update_state_node_name)
        planner_workflow.add_edge(self.agent.update_state_node_name, END)

        # Define entry point
        planner_workflow.set_conditional_entry_point(
            self.agent.new_deliverable_check,
            {
                self.agent.task_breakdown_node_name: self.agent.task_breakdown_node_name,
                self.agent.requirements_analyzer_node_name: self.agent.requirements_analyzer_node_name,
                self.agent.issues_preparation_node_name: self.agent.issues_preparation_node_name
            }
        )

        return planner_workflow

    def get_current_state(self):
        """ Returns the current state dictionary of the agent """

        return self.agent.state
