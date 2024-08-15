"""
Constants used by the project.
"""
import os
from dataclasses import dataclass
from enum import Enum, EnumType
from typing import Any, Dict, Union

from dotenv import load_dotenv
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI

load_dotenv()

@dataclass
class GraphInfo:
    """
    Class that holds information about a graph.

    Attributes:
        graph_name (str): The name of the graph.
        graph_id (str): The unique identifier of the graph.
    """
    graph_name: str
    graph_id: str

@dataclass
class AgentInfo:
    """
    Class that holds information about an agent.

    Attributes:
        agent_name (str): The name of the agent.
        agent_id (str): The unique identifier of the agent.
    """

    agent_name: str
    agent_id: str

class LLMConfig:
    """
    Configuration for a Language Model (LLM).

    This class encapsulates the settings required to initialize an LLM instance.

    Attributes:
        model (str): The model name or identifier.
        temperature (float): The temperature setting for the model's responses.
        max_retries (int): The maximum number of retries for the model.
        streaming (bool): Whether streaming is enabled for the model.
        model_kwargs (Dict[str, Any]): Additional keyword arguments for the model.
    """

    def __init__(self, model: str, temperature: float, max_retries: int, streaming: bool, model_kwargs: Dict[str, Any]):
        """
        Initializes the LLM configuration with the given parameters.

        Args:
            model (str): The model name or identifier.
            temperature (float): The temperature setting for the model's responses.
            max_retries (int): The maximum number of retries for the model.
            streaming (bool): Whether streaming is enabled for the model.
            model_kwargs (Dict[str, Any]): Additional keyword arguments for the model.
        """
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self.streaming = streaming
        self.model_kwargs = model_kwargs

    def create_llm(self) -> Union[ChatOpenAI, ChatOllama]:
        """
        Creates and returns an instance of the configured LLM.

        Returns:
            ChatOpenAI: An instance of ChatOpenAI.

        Raises:
            ValueError: If the model configuration is not supported or is not for ChatOpenAI.
        """
        if self.model.startswith("gpt"):
            return ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                max_retries=self.max_retries,
                streaming=self.streaming,
                model_kwargs=self.model_kwargs
            )
        else:
            raise ValueError(f"Unsupported model configuration: {self.model}. Only ChatOpenAI is currently supported.")
        
class AgentConfig(AgentInfo):
    """
    Configuration for an agent, including its LLM settings and an optional thread ID.

    Attributes:
        agent_name (str): The name of the agent.
        agent_id (str): The unique identifier of the agent.
        llm (Union[ChatOpenAI, ChatOllama]): The LLM instance associated with the agent.
        thread_id (Union[int, None]): Optional thread ID for the agent.
    """

    def __init__(self, agent_name: str, agent_id: str, llm_config: LLMConfig) -> None:
        """
        Initializes the agent configuration with the given parameters.

        Args:
            agent_name (str): The name of the agent.
            agent_id (str): The unique identifier of the agent.
            llm_config (LLMConfig): The LLM configuration for this agent.
        """
        super().__init__(agent_name, agent_id)
        self.llm: Union[ChatOpenAI, ChatOllama] = llm_config.create_llm()
        self.thread_id: Union[int, None] = None

    def set_thread_id(self, thread_id: int) -> None:
        """
        Sets the thread ID for this agent.

        Args:
            thread_id (int): The thread ID to be set.
        """
        self.thread_id = thread_id

class ProjectGraphs(Enum):
    """
    Enum that holds all the graphs used by the project.

    Attributes:
        supervisor (GraphInfo): Information about the Supervisor Graph.
        architect (GraphInfo): Information about the Solution Architect Graph.
        coder (GraphInfo): Information about the Software Engineer Graph.
        rag (GraphInfo): Information about the Standards Extractor Graph.
        planner (GraphInfo): Information about the Project Planner Graph.
        tester (GraphInfo): Information about the Unit Tester Graph.
        modernizer (GraphInfo): Information about the AST Generator Graph.
    """
    supervisor = GraphInfo("Supervisor Graph", "GRPH_01_SUP")
    architect = GraphInfo("Solution Architect Graph", "GRPH_02_ARC")
    coder = GraphInfo("Software Engineer Graph", "GRPH_03_ENG")
    rag = GraphInfo("Standards Extractor Graph", "GRPH_04_RAG")
    planner = GraphInfo("Project Planner Graph", "GRPH_05_PLN")
    tester = GraphInfo("Unit Tester Graph", "GRPH_06_TST")
    modernizer = GraphInfo("AST Generator Graph", "GRPH_07_MOD")

    @property
    def graph_name(self) -> str:
        """
        Returns the name of the graph.

        Returns:
            str: The name of the graph.
        """
        return self.value.graph_name

    @property
    def graph_id(self) -> str:
        """
        Returns the unique identifier of the graph.

        Returns:
            str: The unique identifier of the graph.
        """
        return self.value.graph_id

class ProjectAgents(Enum):
    """
    Enum that holds all the agents used by the project.

    Attributes:
        supervisor (AgentInfo): Information about the Project Supervisor agent.
        architect (AgentInfo): Information about the Solution Architect agent.
        coder (AgentInfo): Information about the Software Engineer agent.
        rag (AgentInfo): Information about the Standards Extractor agent.
        planner (AgentInfo): Information about the Project Planner agent.
        tester (AgentInfo): Information about the Unit Tester agent.
        modernizer (AgentInfo): Information about the AST Generator agent.
        human (AgentInfo): Information about the Human In The Loop agent.
    """

    supervisor = AgentInfo("Project Supervisor", "SUP_01")
    architect = AgentInfo("Solution Architect", "ARC_02")
    coder = AgentInfo("Software Engineer", "ENG_03")
    rag = AgentInfo("Standards Extractor", "RAG_04")
    planner = AgentInfo("Project Planner", "PLN_05")
    tester = AgentInfo("Unit Tester", "TST_06")
    modernizer = AgentInfo("AST Generator", "MOD_07")
    human = AgentInfo("Human Loop", "HUM_08")

    @property
    def agent_name(self) -> str:
        """
        Returns the name of the agent.

        Returns:
            str: The name of the agent.
        """
        return self.value.agent_name

    @property
    def agent_id(self) -> str:
        """
        Returns the unique identifier of the agent.

        Returns:
            str: The unique identifier of the agent.
        """
        return self.value.agent_id
    
AGENTS_CONFIG: Dict[str, AgentConfig] = {
    ProjectAgents.supervisor.agent_id: AgentConfig(
        ProjectAgents.supervisor.agent_name,
        ProjectAgents.supervisor.agent_id,
        LLMConfig(
            model="gpt-4o-2024-05-13",
            temperature=0,
            max_retries=5,
            streaming=False,
            model_kwargs={"seed": 4000, "top_p": 0.8}
        )
    ),
    ProjectAgents.architect.agent_id: AgentConfig(
        ProjectAgents.architect.agent_name,
        ProjectAgents.architect.agent_id,
        LLMConfig(
            model="gpt-4o-2024-05-13",
            temperature=0.3,
            max_retries=5,
            streaming=True,
            model_kwargs={"seed": 4000, "top_p": 0.4}
        )
    ),
    ProjectAgents.coder.agent_id: AgentConfig(
        ProjectAgents.coder.agent_name,
        ProjectAgents.coder.agent_id,
        LLMConfig(
            model="gpt-4o-2024-05-13",
            temperature=0.3,
            max_retries=5,
            streaming=True,
            model_kwargs={"seed": 4000, "top_p": 0.4}
        )
    ),
    ProjectAgents.rag.agent_id: AgentConfig(
        ProjectAgents.rag.agent_name,
        ProjectAgents.rag.agent_id,
        LLMConfig(
            model="gpt-4o-2024-05-13",
            temperature=0,
            max_retries=5,
            streaming=True,
            model_kwargs={"seed": 4000, "top_p": 0.3}
        )
    ),
    ProjectAgents.planner.agent_id: AgentConfig(
        ProjectAgents.planner.agent_name,
        ProjectAgents.planner.agent_id,
        LLMConfig(
            model="gpt-4o-2024-05-13",
            temperature=0.3,
            max_retries=5,
            streaming=True,
            model_kwargs={"seed": 4000, "top_p": 0.6}
        )
    ),
    ProjectAgents.tester.agent_id: AgentConfig(
        ProjectAgents.tester.agent_name,
        ProjectAgents.tester.agent_id,
        LLMConfig(
            model="gpt-4o-2024-05-13",
            temperature=0.3,
            max_retries=5,
            streaming=True,
            model_kwargs={"seed": 4000, "top_p": 0.6}
        )
    ),
    ProjectAgents.modernizer.agent_id: AgentConfig(
        ProjectAgents.modernizer.agent_name,
        ProjectAgents.modernizer.agent_id,
        LLMConfig(
            model="gpt-4o-2024-05-13",
            temperature=0.3,
            max_retries=5,
            streaming=True,
            model_kwargs={"seed": 4000, "top_p": 0.6}
        )
    ),
    ProjectAgents.human.agent_id: AgentConfig(
        ProjectAgents.human.agent_name,
        ProjectAgents.human.agent_id,
        LLMConfig(
            model="gpt-4o-2024-05-13",
            temperature=0.3,
            max_retries=5,
            streaming=True,
            model_kwargs={"seed": 4000, "top_p": 0.6}
        )
    )
}

class ProjectConfig:
    """
    Configuration for the entire project, including agent configurations and vector database settings.

    Attributes:
        agents (Enum): Enum containing all project agents.
        agents_config (Dict[str, AgentConfig]): Dictionary mapping agent IDs to their configurations.
        vector_db_collections (Dict[str, str]): Dictionary mapping vector DB collection names to their paths.
    """

    def __init__(self) -> None:
        """
        Initializes the project configuration with predefined agents, their configurations,
        and vector database collection paths.
        """
        self.graphs = ProjectGraphs
        self.agents = ProjectAgents
        self.agents_config = AGENTS_CONFIG
        self.vector_db_collections = {
            'MISMO-version-3.6-docs': os.path.join(os.getcwd(), "vector_collections")
        }
    
    def __str__(self) -> str:
        """
        Returns a detailed string representation of the ProjectConfig instance.

        Returns:
            str: A structured string representation of the ProjectConfig instance, showing its attributes and their values.
        """
        def format_enum(enum_type: Enum) -> str:
            """
            Formats the enum members and their values for output.

            Args:
                enum_type (EnumMeta): The enum type to format.

            Returns:
                str: A formatted string of enum members and their values.
            """
            return "\n".join(f"  {name}: {member.value}" for name, member in enum_type.__members__.items())

        def format_agent_config(config: Any) -> str:
            """
            Formats the AgentConfig object for output.

            Args:
                config (Any): The AgentConfig object to format.

            Returns:
                str: A formatted string representation of the AgentConfig object.
            """
            if isinstance(config, AgentConfig):
                llm_info = (
                    f"client=<client_instance> "
                    f"async_client=<async_client_instance> "
                    f"model_name='{config.llm.model_name}' "
                    f"temperature={config.llm.temperature} "
                    f"model_kwargs={config.llm.model_kwargs} "
                    f"openai_api_key=SecretStr('**********') "
                    f"openai_proxy='{config.llm.openai_proxy}' "
                    f"max_retries={config.llm.max_retries} "
                    f"streaming={config.llm.streaming}"
                )
                return (f"AgentConfig(\n"
                        f"  agent_name='{config.agent_name}',\n"
                        f"  agent_id='{config.agent_id}',\n"
                        f"  llm={llm_info},\n"
                        f"  thread_id={getattr(config, 'thread_id', 'None')}\n"
                        f")")
            return str(config)

        def format_value(value: Any) -> str:
            """
            Formats the value for output. Handles dictionaries, lists, enums, and custom objects specifically.

            Args:
                value (Any): The value to format.

            Returns:
                str: A formatted string representation of the value.
            """
            if isinstance(value, EnumType):
                return format_enum(value)
            elif isinstance(value, dict):
                return "\n".join(f"  {k}:\n{format_value(v)}" for k, v in value.items())
            elif isinstance(value, list):
                return "\n".join(f"  - {format_value(v)}" for v in value)
            elif isinstance(value, AgentConfig):
                return format_agent_config(value)
            else:
                return str(value)

        attributes = vars(self)
        formatted_attributes = {
            key: format_value(value) for key, value in attributes.items()
        }
        
        # Create a more informative string representation
        return (
            "Project Configuration:\n"
            "====================\n" +
            "\n".join(
                f"{key}:\n{value}" if isinstance(value, (dict, list)) else f"{key}: {value}"
                for key, value in formatted_attributes.items()
            )
        )
