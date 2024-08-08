from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from typing import Dict, Union

from agents.agent.graph import Graph
from agents.supervisor.supervisor_agent import SupervisorAgent
from agents.supervisor.supervisor_state import SupervisorState
from configs.project_config import AgentConfig
from configs.project_config import ProjectGraphs
from utils.logs.logging_utils import logger


class SupervisorWorkflow(Graph[SupervisorAgent]):
    def __init__(self, 
                llm: Union[ChatOpenAI, ChatOllama],
                collections: dict[str, str], 
                user_input: str, rag_try_limit: int, 
                project_path: str, persistance_db_path: str,
                agents_config: Dict[str, AgentConfig]):
    
        super().__init__(
            ProjectGraphs.supervisor.graph_name, 
            ProjectGraphs.supervisor.graph_id,
            SupervisorAgent(llm, collections, user_input, rag_try_limit, project_path, persistance_db_path, agents_config),
            persistance_db_path
        )

        self.compile_graph_with_persistence()

    def define_graph(self) -> StateGraph:

        supervisor_workflow = StateGraph(SupervisorState)
        
        # Define the nodes
        supervisor_workflow.add_node("kickoff", self.agent.instantiate_team_members)
        supervisor_workflow.add_node("Architect", self.agent.call_architect)
        supervisor_workflow.add_node("Coder", self.agent.call_coder)
        supervisor_workflow.add_node("RAG", self.agent.call_rag)
        supervisor_workflow.add_node("Planner", self.agent.call_planner)
        supervisor_workflow.add_node("update_state", self.agent.update_state)
        supervisor_workflow.add_node("Supervisor", self.agent.call_supervisor)
        supervisor_workflow.add_node("Human", self.agent.call_human)

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
                                                      "call_supervisor": 'Supervisor',
                                                      "update_state" : "update_state",
                                                      "Human" : 'Human'
                                                  })
        supervisor_workflow.add_edge("RAG","Supervisor")
        supervisor_workflow.add_edge("Architect","Supervisor")
        supervisor_workflow.add_edge("Planner","Supervisor")
        supervisor_workflow.add_edge("Coder","Supervisor")
        supervisor_workflow.add_edge("Human","Supervisor")
        supervisor_workflow.add_edge("update_state", END)
        
        return supervisor_workflow
    
    def get_current_state(self):
        """ Returns the current state dictionary of the agent """
        return self.agent.state
