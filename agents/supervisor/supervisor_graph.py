from langgraph.graph import StateGraph, END
from .supervisor_state import SupervisorState
from .supervisor_agent import SupervisorAgent

class SupervisorWorkflow():
    def __init__(self, llm):
        self.agent = SupervisorAgent(llm, "Do Something")
        supervisor_workflow = StateGraph(SupervisorState)
        # Define the nodes
        supervisor_workflow.add_node("kickoff", self.agent.instantiate_team_members)
        supervisor_workflow.add_node("Architect", self.agent.call_architect)
        supervisor_workflow.add_node("Coder", self.agent.call_coder)
        supervisor_workflow.add_node("RAG", self.agent.call_rag)
        supervisor_workflow.add_node("Planner", self.agent.call_planner)
        supervisor_workflow.add_node("update_state", self.agent.update_state)
        
        # Build graph
        supervisor_workflow.set_entry_point("kickoff")
        supervisor_workflow.add_conditional_edges("kickoff",
                                                  self.agent.delegator,
                                                  {
                                                      "Architect" : "Architect",
                                                      "Coder" : "Coder",
                                                      "RAG" : "RAG",
                                                      "Planner" : "Planner",
                                                      "update_state" : "update_state"
                                                  })
        supervisor_workflow.add_edge("update_state",END)

        # Compile
        supervisor_workflow.sup_app = supervisor_workflow.compile()

    def get_current_state(self):
        """ Returns the current state dictionary of the agent """
        return self.agent.state
