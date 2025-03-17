from langgraph.graph import END, StateGraph

from agents.base.base_graph import BaseGraph
from agents.supervisor.supervisor_agent import SupervisorAgent
from agents.supervisor.supervisor_state import SupervisorState
from llms.llm import LLM
from utils.logs.logging_utils import logger


class SupervisorWorkflow(BaseGraph[SupervisorAgent]):
    """
    A workflow class that defines the state graph for the SupervisorAgent.

    The SupervisorWorkflow manages the project's lifecycle, delegating tasks 
    to various agents (e.g., Architect, Coder, Reviewer) and ensuring smooth 
    transitions between different project phases.
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
        Initializes the SupervisorWorkflow.

        Args:
            graph_id (str): Unique identifier for the graph.
            graph_name (str): Name of the workflow graph.
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Name of the agent.
            llm (LLM): An instance of the language learning model.
            persistence_db_path (str): Path to the persistence database.
        """
        logger.info(f"Initializing SupervisorWorkflow with graph_id: {graph_id}, graph_name: {graph_name}")
        super().__init__(
            graph_id,
            graph_name,
            SupervisorAgent(agent_id, agent_name, llm),
            persistance_db_path
        )
        logger.info("Compiling the state graph with persistence.")
        self.compile_graph_with_persistence()

    def define_graph(self) -> StateGraph:
        """
        Defines the state graph for the SupervisorWorkflow.

        Returns:
            StateGraph: The defined state graph for the workflow.
        """
        logger.info("Defining the state graph for the SupervisorWorkflow.")
        supervisor_workflow = StateGraph(SupervisorState)
        
        # Define the nodes
        supervisor_workflow.add_node("kickoff", self.agent.instantiate_state)
        supervisor_workflow.add_node("Architect", self.agent.call_architect)
        supervisor_workflow.add_node("Coder", self.agent.call_coder)
        supervisor_workflow.add_node("Reviewer", self.agent.call_reviewer)
        supervisor_workflow.add_node("RAG", self.agent.call_rag)
        supervisor_workflow.add_node("Planner", self.agent.call_planner)
        supervisor_workflow.add_node("update_state", self.agent.update_state)
        supervisor_workflow.add_node("Supervisor", self.agent.call_supervisor)
        supervisor_workflow.add_node("Human", self.agent.call_human)
        supervisor_workflow.add_node("TestGenerator", self.agent.call_test_code_generator)

        # Build graph
        logger.info(f"Setting entry point of the graph to 'kickoff'.")
        supervisor_workflow.set_entry_point("kickoff")
        
        supervisor_workflow.add_edge("kickoff", "Supervisor")
        supervisor_workflow.add_conditional_edges(
            "Supervisor",
            self.agent.delegator,
            {
                "call_architect" : "Architect",
                "call_coder" : "Coder",
                "call_rag" : "RAG",
                "call_planner" : "Planner",
                "call_reviewer": "Reviewer",
                "call_supervisor": 'Supervisor',
                "update_state" : "update_state",
                "Human" : 'Human',
                "call_test_code_generator" : "TestGenerator"
            }
        )
        supervisor_workflow.add_edge("RAG", "Supervisor")
        supervisor_workflow.add_edge("Reviewer", "Supervisor")
        supervisor_workflow.add_edge("Architect", "Supervisor")
        supervisor_workflow.add_edge("Planner", "Supervisor")
        supervisor_workflow.add_edge("Coder", "Supervisor")
        supervisor_workflow.add_edge("TestGenerator", "Supervisor")
        supervisor_workflow.add_edge("Human", "Supervisor")
        supervisor_workflow.add_edge("update_state", END)

        logger.info("State graph definition completed.")
        return supervisor_workflow
   
    def get_current_state(self):
        """
        Returns the current state dictionary of the agent.

        Returns:
            dict: The current state of the SupervisorAgent.
        """
        logger.debug("Fetching the current state of the SupervisorAgent.")
        return self.agent.state
