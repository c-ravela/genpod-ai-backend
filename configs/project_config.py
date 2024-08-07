"""
Constants that gonna be used by the project
"""
import os

from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama

from typing import Union, Dict, Any

from dotenv import load_dotenv
from enum import Enum

load_dotenv()

class GraphInfo:
    """Class that holds all the agents used by the project"""

    graph_name: str # name fo the graph
    graph_id: str # id of the graph

    def __init__(self, graph_name, graph_id) -> None:
        self.graph_name = graph_name
        self.graph_id = graph_id

class AgentInfo:
    """Class that holds all the agents used by the project"""

    agent_name: str # name fo the agent
    agent_id: str # id of the agent

    def __init__(self, agent_name, agent_id) -> None:
        self.agent_name = agent_name
        self.agent_id = agent_id

class AgentConfig(AgentInfo):
    """Agent configuration"""

    thread_id: int # thread_id for this agenth
    llm: Union[ChatOpenAI, ChatOllama]

    def __init__(self, agent_name, agent_id, llm) -> None:
        """
        """

        super().__init__(agent_name, agent_id)
        self.llm = llm
        
    def set_thread_id(self, thread_id) -> None:
        """Set the thread_id for this agent"""

        self.thread_id = thread_id

class ProjectGraphs(Enum):
    """Enum that holds all the graph used by the project"""

    supervisor: GraphInfo = GraphInfo("Supervisor Graph","1_supervisor_graph")
    architect: GraphInfo = GraphInfo("Solution Architect Graph", "2_architect_graph")
    coder: GraphInfo = GraphInfo("Software Programmer Graph", "3_coder_graph")
    rag: GraphInfo = GraphInfo("RAG Graph", "4_rag_graph")
    planner: GraphInfo = GraphInfo("Planner Graph", "5_planner_graph")
    tester: GraphInfo = GraphInfo("Tester Graph", "6_tester_graph")

    @property
    def graph_name(self) -> str:
        return self.value.graph_name

    @property
    def graph_id(self) -> str:
        return self.value.graph_id

class ProjectAgents(Enum): 
    """Class that holds all the agents used by the project"""

    supervisor: AgentInfo = AgentInfo("Supervisor", "1_supervisor_agent")
    architect: AgentInfo = AgentInfo("Solution Architect", "2_architect_agent")
    coder: AgentInfo = AgentInfo("Software Programmer", "3_coder_agent")
    rag: AgentInfo = AgentInfo("RAG", "4_rag_agent")
    planner: AgentInfo = AgentInfo("Planner", "5_planner_agent")
    tester: AgentInfo = AgentInfo("Tester", "6_tester_agent")

    @property
    def agent_name(self) -> str:
        return self.value.agent_name
    
    @property
    def agent_id(self) -> str:
        return self.value.agent_id
    
AGENTS_CONFIG: dict[str, AgentConfig] = {
    ProjectAgents.supervisor.agent_id: AgentConfig(
        ProjectAgents.supervisor.agent_name,
        ProjectAgents.supervisor.agent_id,
        ChatOpenAI(
            model="gpt-4o-2024-05-13", 
            temperature=0, 
            max_retries=5,
            model_kwargs={
                "seed": 4000,
                "top_p": 0.8
            }
        )
    ),
    ProjectAgents.architect.agent_id: AgentConfig(
        ProjectAgents.architect.agent_name,
        ProjectAgents.architect.agent_id,
        ChatOpenAI(
            model="gpt-4o-2024-05-13", 
            temperature=0.3, 
            max_retries=5, 
            streaming=True,
            model_kwargs={
                "seed": 4000,
                "top_p": 0.4
            }
        )
    ),
    ProjectAgents.coder.agent_id: AgentConfig(
        ProjectAgents.coder.agent_name,
        ProjectAgents.coder.agent_id,
        ChatOpenAI(
            model="gpt-4o-2024-05-13",
            temperature=0.3,
            max_retries=5,
            streaming=True,
            model_kwargs={
                "seed": 4000,
                "top_p": 0.4
            }
        )
    ),
    ProjectAgents.rag.agent_id: AgentConfig(
        ProjectAgents.rag.agent_name,
        ProjectAgents.rag.agent_id,
        ChatOpenAI(
            model="gpt-4o-2024-05-13", 
            temperature=0, 
            max_retries=5, 
            streaming=True, 
            model_kwargs={
                "seed": 4000,
                "top_p": 0.3
            }
        )
    ),
    ProjectAgents.planner.agent_id: AgentConfig(
        ProjectAgents.planner.agent_name,
        ProjectAgents.planner.agent_id,
        ChatOpenAI(
            model="gpt-4o-2024-05-13",
            temperature=0.3,
            max_retries=5,
            streaming=True,
            model_kwargs={
                "seed": 4000,
                "top_p": 0.6
            }
        )
    ),
    ProjectAgents.tester.agent_id: AgentConfig(
        ProjectAgents.tester.agent_name,
        ProjectAgents.tester.agent_id,
        ChatOpenAI(
            model="gpt-4o-2024-05-13",
            temperature=0.3,
            max_retries=5,
            streaming=True,
            model_kwargs={
                "seed": 4000,
                "top_p": 0.6
            } 
        )
    )
}

class ProjectConfig:
    """
    """

    def __init__(self):
        self.agents = ProjectAgents
        self.agents_config = AGENTS_CONFIG
        self.vector_db_collections = {'MISMO-version-3.6-docs': os.path.join(os.getcwd(), "vector_collections")}
