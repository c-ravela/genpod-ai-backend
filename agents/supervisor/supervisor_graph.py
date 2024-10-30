from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from agents.agent.graph import Graph
from agents.supervisor.supervisor_agent import SupervisorAgent
from agents.supervisor.supervisor_state import SupervisorState
from llms.llm import LLM


class SupervisorWorkflow(Graph[SupervisorAgent]):
    def __init__(self, graph_id: str, graph_name: str, agent_id: str, agent_name: str, llm: LLM, persistance_db_path: str):
    
        super().__init__(
            graph_id,
            graph_name,
            SupervisorAgent(agent_id, agent_name, llm),
            persistance_db_path
        )

        self.compile_graph_with_persistence()

    def define_graph(self) -> StateGraph:

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
        supervisor_workflow.add_node("TestGenerator",self.agent.call_test_code_generator)

        # Build graph
        supervisor_workflow.set_entry_point("kickoff")
        supervisor_workflow.add_edge("kickoff","Supervisor")
        supervisor_workflow.add_conditional_edges("Supervisor",
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
                                                   })
        supervisor_workflow.add_edge("RAG", "Supervisor")
        supervisor_workflow.add_edge("Reviewer", "Supervisor")
        supervisor_workflow.add_edge("Architect", "Supervisor")
        supervisor_workflow.add_edge("Planner", "Supervisor")
        supervisor_workflow.add_edge("Coder", "Supervisor")
        supervisor_workflow.add_edge("TestGenerator", "Supervisor")
        supervisor_workflow.add_edge("Human", "Supervisor")
        supervisor_workflow.add_edge("update_state", END)
       
        return supervisor_workflow
   
    def get_current_state(self):
        """Returns the current state dictionary of the agent"""
        return self.agent.state
