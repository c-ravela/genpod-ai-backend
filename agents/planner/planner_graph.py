from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from agents.agent.graph import Graph
from agents.planner.planner_agent import PlannerAgent
from agents.planner.planner_state import PlannerState
from configs.project_config import ProjectGraphs
from models.models import Task


class PlannerWorkFlow(Graph[PlannerAgent]):
    def __init__(self, llm: ChatOpenAI, persistance_db_path: str):
        super().__init__(
            ProjectGraphs.planner.graph_id,
            ProjectGraphs.planner.graph_name, 
            PlannerAgent(llm),
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
