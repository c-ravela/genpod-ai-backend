"""
Constants that gonna be used by the project
"""
import os

from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama

from typing import Union

from dotenv import load_dotenv

load_dotenv()

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

class ProjectAgents: 
    """Class that holds all the agents used by the project"""

    def __init__(self):
        self.supervisor = AgentInfo("Supervisor","1_supervisor")

        self.architect = AgentInfo("Solution Architect", "2_architect")
        
        self.coder = AgentInfo("Software Programmer", "3_coder")

        self.rag = AgentInfo("RAG", "4_rag")

        self.planner = AgentInfo("Planner", "5_planner")

        self.tester = AgentInfo("Tester", "6_tester")

AGENTS_CONFIG: dict[str, AgentConfig] = {
    ProjectAgents().supervisor.agent_id: AgentConfig(
        ProjectAgents().supervisor.agent_name,
        ProjectAgents().supervisor.agent_id,
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
    ProjectAgents().architect.agent_id: AgentConfig(
        ProjectAgents().architect.agent_name,
        ProjectAgents().architect.agent_id,
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
    ProjectAgents().coder.agent_id: AgentConfig(
        ProjectAgents().coder.agent_name,
        ProjectAgents().coder.agent_id,
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
    ProjectAgents().rag.agent_id: AgentConfig(
        ProjectAgents().rag.agent_name,
        ProjectAgents().rag.agent_id,
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
    ProjectAgents().planner.agent_id: AgentConfig(
        ProjectAgents().planner.agent_name,
        ProjectAgents().planner.agent_id,
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
    ProjectAgents().tester.agent_id: AgentConfig(
        ProjectAgents().tester.agent_name,
        ProjectAgents().tester.agent_id,
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
        self.agents = ProjectAgents()
        self.agents_config = AGENTS_CONFIG
        self.vector_db_collections = {'MISMO-version-3.6-docs': os.path.join(os.getcwd(), "vector_collections")}
