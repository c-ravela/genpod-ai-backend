from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from agents.supervisor.supervisor_agent import SupervisorAgent
from agents.supervisor.supervisor_state import SupervisorState
from utils.logs.logging_utils import logger


class SupervisorWorkflow():
    def __init__(self, llm, collections, thread_id, members, memberids, user_input, rag_try_limit, project_path, persistance_db_path: str):
        self.collections = collections
        self.thread_id = thread_id
        self.members = members
        self.memberids = memberids
        self.user_input = user_input

        self.memory = SqliteSaver.from_conn_string(persistance_db_path)

        self.agent = SupervisorAgent(llm, self.collections, self.members, self.memberids, self.user_input, rag_try_limit, project_path, persistance_db_path)
        self.supervisor_workflow = StateGraph(SupervisorState)
        
        # Define the nodes
        self.supervisor_workflow.add_node("kickoff", self.agent.instantiate_team_members)
        self.supervisor_workflow.add_node("Architect", self.agent.call_architect)
        self.supervisor_workflow.add_node("Coder", self.agent.call_coder)
        self.supervisor_workflow.add_node("RAG", self.agent.call_rag)
        self.supervisor_workflow.add_node("Planner", self.agent.call_planner)
        self.supervisor_workflow.add_node("update_state", self.agent.update_state)
        self.supervisor_workflow.add_node("Supervisor", self.agent.call_supervisor)
        self.supervisor_workflow.add_node("Human", self.agent.call_human)

        # Build graph
        self.supervisor_workflow.set_entry_point("kickoff")
        self.supervisor_workflow.add_edge("kickoff","Supervisor")
        self.supervisor_workflow.add_conditional_edges("Supervisor",
                                                  self.agent.delegator,
                                                  {
                                                      "call_architect" : "Architect",
                                                      "call_coder" : "Coder",
                                                      "call_rag" : "RAG",
                                                      "call_planner" : "Planner",
                                                      "call_supervisor": 'Supervisor',
                                                      "update_state" : "update_state",
                                                      "Human" : 'Human'
                                                  })
        self.supervisor_workflow.add_edge("RAG","Supervisor")
        self.supervisor_workflow.add_edge("Architect","Supervisor")
        self.supervisor_workflow.add_edge("Planner","Supervisor")
        self.supervisor_workflow.add_edge("Coder","Supervisor")
        self.supervisor_workflow.add_edge("Human","Supervisor")
        self.supervisor_workflow.add_edge("update_state", END)
        # Compile

        self.sup_app = self.supervisor_workflow.compile(checkpointer=self.memory)

    def get_current_state(self):
        """ Returns the current state dictionary of the agent """
        return self.agent.state
