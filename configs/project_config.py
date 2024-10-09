import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator

from llms.factory import llm_factory
from llms.llm import LLM
from utils.yaml_utils import read_yaml

# Supported LLMs categorized by provider
SUPPORTED_LLMS = {
    'openai': [
        'chatgpt-40-latest',
        'gpt-4o-2024-08-06',
        'gpt-4o-2024-05-13'
    ],
    'ollama': [
        'llama3'
    ],
    'anthropic': [
        'claude-instant-1.2'
    ]
}

def check_provider(provider: str) -> None:
    """
    Checks if the specified provider is supported.

    Args:
        provider (str): The name of the provider to check.

    Raises:
        ValueError: If the provider is not supported.
    """
    if provider not in SUPPORTED_LLMS:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers are: {list(SUPPORTED_LLMS.keys())}")

def check_model(provider: str, model: str) -> None:
    """
    Checks if the specified model is supported for the given provider.

    Args:
        provider (str): The name of the provider.
        model (str): The name of the model.

    Raises:
        ValueError: If the model is not supported for the provider.
    """
    if model not in SUPPORTED_LLMS.get(provider, []):
        raise ValueError(f"Unsupported model: {model} for provider {provider}. Supported models for {provider} are: {SUPPORTED_LLMS[provider]}")
    
class LLMConfig(BaseModel):
    """Configuration for a specific LLM."""
    provider: str
    model: str
    config: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('provider')
    def validate_provider(cls, value):
        """
        Validates the provider field to ensure it is supported.

        Args:
            cls: The class reference.
            value (str): The provider to validate.

        Returns:
            str: The validated provider.

        Raises:
            ValueError: If the provider is not supported.
        """
        check_provider(value)
        return value

    @field_validator('model')
    def validate_model(cls, value, values):
        """
        Validates the model field based on the selected provider.

        Args:
            cls: The class reference.
            value (str): The model to validate.
            values (Dict[str, Any]): The other fields in the model to access provider.

        Returns:
            str: The validated model.

        Raises:
            ValueError: If the model is not supported for the provider.
        """
        provider = values.data.get('provider')
        check_model(provider, value)
        return value

class ProviderModelConfig(BaseModel):
    """Configuration for a specific provider's model."""
    
    name: str
    description: str
    api_key: str = Field(required=False, default=None)

class ProviderSetting(BaseModel):
    """Settings for a provider."""
    
    api_key: str = Field(required=False, default=None)
    max_retries: int = Field(ge=1, required=False, default=None)
    retry_backoff: int  = Field(ge=0, required=False, default=None)

class ProviderConfig(BaseModel):
    """Configuration for a specific provider."""

    name: str
    setting: ProviderSetting = Field(default=None)
    models: dict[str, ProviderModelConfig] = Field(default=None)

    @field_validator("name")
    def validate_name(cls, value):
        """
        Validates the provider name.

        Args:
            cls: The class reference.
            value (str): The provider name to validate.

        Returns:
            str: The validated provider name.

        Raises:
            ValueError: If the provider name is not supported.
        """
        check_provider(value)
        return value

class AgentConfig(BaseModel):
    """Configuration for an agent."""

    description: str
    llm_config: LLMConfig = Field(required=False, default=None)

class DefaultConfig(BaseModel):
    """Default configuration settings for the project."""
    
    llm_config: LLMConfig
    max_retries: int = Field(ge=1, required=True)
    retry_backoff: int  = Field(ge=0, required=True)
    max_graph_recursion_limit: Optional[int] = Field(ge=1, required=True)

class GenpodConfig(BaseModel):
    """Configuration for the Genpod project."""
    
    default: DefaultConfig
    providers: Dict[str, ProviderConfig]
    agents: Dict[str, AgentConfig]
    vector_collections_name: str
    max_graph_recursion_limit: Optional[int] = Field(
        ge=1, 
        required=False, 
        default=None
    )

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
        alias (Optional[str]): An optional alias for the agent.
        description (Optional[str]): An optional description of the agent.
        thread_id (Union[int, None]): The ID of the thread associated with the agent, if any.
        llm (LLM): The LLM instance associated with the agent.
    """
    agent_name: str
    agent_id: str
    alias: str = ""
    description: str = ""
    thread_id: Union[int, None] = None
    llm: LLM = None
  
    def set_llm(self, l: LLM) -> None:
        """
        Sets the thread ID for this agent.

        Args:
            thread_id (int): The thread ID to be set.
        """
        self.llm = l

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
        tests_generator (GraphInfo): Information about the Unit Tester Graph.
        modernizer (GraphInfo): Information about the Knowledge Graph Generator Graph.
        reviewer (GraphInfo): Information about the Code Reviewer Graph.
    """

    supervisor: GraphInfo = GraphInfo("Project Supervisor Graph", "GRPH_01_SUP")
    architect: GraphInfo = GraphInfo("Solution Architect Graph", "GRPH_02_ARC")
    coder: GraphInfo = GraphInfo("Software Engineer Graph", "GRPH_03_ENG")
    rag: GraphInfo = GraphInfo("Document Repository Manager Graph", "GRPH_04_RAG")
    planner: GraphInfo = GraphInfo("Project Planner Graph", "GRPH_05_PLN")
    tests_generator: GraphInfo = GraphInfo("Unit Tester Graph", "GRPH_06_TST")
    modernizer: GraphInfo = GraphInfo("Knowledge Graph Generator Graph", "GRPH_07_MOD")
    reviewer: GraphInfo = GraphInfo("Code Reviewer Graph", "GRPH_08_REV")

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
        tests_generator (AgentInfo): Information about the Unit Tester agent.
        modernizer (AgentInfo): Information about the Knowledge graph Generator agent.
        human (AgentInfo): Information about the Human In The Loop agent.
        reviwer (AgentInfo): Information about the code reviewing agent
    """

    supervisor: AgentInfo = AgentInfo(
        agent_name="Project Supervisor", 
        agent_id="SUP_01",
        alias="supervisor",
        description="Coordinates with the team, assigns tasks, and guides the team toward successful project completion."
    )

    architect: AgentInfo = AgentInfo(
        agent_name="Solution Architect", 
        agent_id="ARC_02",
        alias="architect",
        description="Defines the project requirements and outlines the architectural framework."
    )

    coder: AgentInfo = AgentInfo(
        agent_name="Software Engineer", 
        agent_id="ENG_03",
        alias="coder",
        description="Develops and writes code to the tasks assigned."
    )

    rag: AgentInfo = AgentInfo(
        agent_name="Document Repository Manager", 
        agent_id="RAG_04",
        alias="rag",
        description="Oversees the vector database, manages document and file storage, and provides relevant information in response to queries."
    )

    planner: AgentInfo = AgentInfo(
        agent_name="Project Planner", 
        agent_id="PLN_05",
        alias="planner",
        description="Creates detailed plans for task execution, based on requirements provided."
    )

    tests_generator: AgentInfo = AgentInfo(
        agent_name="Unit Tester", 
        agent_id="TST_06",
        alias="tests_generator",
        description="Develops and executes unit test cases to ensure code quality and functionality."
    )

    modernizer: AgentInfo = AgentInfo(
        agent_name="Knowledge Graph Generator", 
        agent_id="MOD_07",
        alias="modernizer",
        description="Generates and maintains the knowledge graph for the project, facilitating data relationships and insights."
    )

    human = AgentInfo(
        agent_name="Human Intervention Specialist", 
        agent_id="HUM_08",
        alias="human",
        description="Provides assistance and oversight when automated systems encounter issues or produce unreliable results."
    )

    reviewer: AgentInfo = AgentInfo(
        agent_name="Code Reviewer",
        agent_id="REV_09",
        alias="reviewer",
        description="Responsible for evaluating code quality and ensuring adherence to coding standards. This includes reviewing code for clean code principles, naming conventions, and compliance with both internal and external standards."
    )

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
    
    @property
    def alias(self) -> str:
        """
        Returns the alias of the agent, if it exists.

        Returns:
            Optional[str]: The alias of the agent, or None if not set.
        """
        return self.value.alias

    @property
    def description(self) -> str:
        """
        Returns the description of the agent, if it exists.

        Returns:
            Optional[str]: The description of the agent, or None if not set.
        """
        return self.value.description
    
    @property
    def thread_id(self) -> int:
        """
        Returns the thread_id associated with the agent.

        Returns:
            LLM: The thread_id instance associated with the agent.
        """
        return self.value.thread_id
    
    @property
    def llm(self) -> LLM:
        """
        Returns the LLM associated with the agent.

        Returns:
            LLM: The LLM instance associated with the agent.
        """
        return self.value.llm
    
    @classmethod
    def get_agent(cls, alias: str) -> AgentInfo:
        """
        Retrieve an agent's information by its alias.

        Args:
            alias (str): The alias of the agent.

        Returns:
            AgentInfo: The corresponding AgentInfo object.
        """

        return cls[alias]
    
    @classmethod
    def get_agent_by_id(cls, agent_id: str) -> Optional[AgentInfo]:
        """
        Retrieve an agent's information by its ID.

        Args:
            agent_id (str): The unique identifier of the agent.

        Returns:
            Optional[AgentInfo]: The corresponding AgentInfo object, or None if not found.
        """
        for agent in cls:
            if agent.value.agent_id == agent_id:
                return agent.value
        return None
    
    @classmethod
    def has_agent(cls, alias: str) -> bool:
        """
        Check if the alias exists in the ProjectAgents enum.

        Args:
            alias (str): The alias of the agent.

        Returns:
            bool: True if the alias exists, False otherwise.
        """
        return any(agent.alias == alias for agent in cls)
    
    def set_llm(self, llm: LLM) -> None:
        """
        Set the LLM instance for the agent.

        Args:
            llm (LLM): The LLM instance to be associated with the agent.

        Returns:
            None
        """
        self.value.set_llm(llm)

    def set_thread_id(self, thread_id: int) -> None:
        """
        Set the thread ID for the agent.

        Args:
            thread_id (int): The thread ID to be associated with the agent.

        Returns:
            None
        """
        self.value.set_thread_id(thread_id)
    
    def __iter__(self):
        """
        Custom iterator to return each enum member's agent info.

        Yields:
            AgentInfo: Yields each AgentInfo object from the enum.
        """
        for agent in ProjectAgents:
            yield agent.value

class ProjectConfig:
    """
    Configuration for the entire project, including agent configurations and vector database settings.

    Attributes:
        agents (Enum): Enum containing all project agents.
        vector_db_collections (Dict[str, str]): Dictionary mapping vector DB collection names to their paths.
    """

    graphs: ProjectGraphs
    agents: ProjectAgents
    vector_db_collections: Dict[str, str] =  {
            'MISMO-version-3.6-docs': os.path.join(os.getcwd(), "vector_collections")
    }
    vector_collections_name: str
    max_graph_recursion_limit: int
    __config_path: str
    __genpod_config: GenpodConfig

    def __init__(self, config_path: str) -> None:
        """
        Initializes the project configuration with predefined agents, their configurations,
        and vector database collection paths.
        """

        self.graphs = ProjectGraphs
        self.agents = ProjectAgents
        self.__config_path = config_path

    def load_config(self) -> None:
        """
        Loads the configuration data from a YAML file and updates the project settings accordingly.
        
        This method reads the YAML configuration from the file path specified during initialization, 
        parses the configuration into the internal `GenpodConfig` structure, and applies the configurations 
        by calling the appropriate update methods.
        """
        try:
            __yaml_data =  read_yaml(self.__config_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {self.__config_path}.")
        except Exception as e:
            raise ValueError(f"Error parsing YAML config: {e}")
    
        self.__genpod_config = GenpodConfig(**__yaml_data)
        self.__update_config()

    def __update_config(self) -> None:
        """
        Updates the project settings based on the loaded configuration data.
        """

        self.vector_collections_name = self.__genpod_config.vector_collections_name
        self.__set__max_graph_recursion_limit()
        self.__update__agents()
        
    def __set__max_graph_recursion_limit(self):
        """
        Sets the maximum recursion limit for graphs, using values from the configuration.
        """

        if self.__genpod_config.max_graph_recursion_limit:
            self.max_graph_recursion_limit = self.__genpod_config.max_graph_recursion_limit
        else:
            self.max_graph_recursion_limit = self.__genpod_config.default.max_graph_recursion_limit
    
    def __update__agents(self) -> None:
        """
        Sets LLM instances for agents based on their configurations.
        """

        for agent, config in self.__genpod_config.agents.items():
            if not self.agents.has_agent(agent):
                raise ValueError(f"Agent {agent} not found in ProjectAgents.")

            llm_config = config.llm_config or self.__genpod_config.default.llm_config
            provider_config = self.__genpod_config.providers[llm_config.provider]
            max_retries, retry_backoff = self.__get_retry_settings(provider_config, self.__genpod_config.default)

            provider = llm_config.provider
            model = llm_config.model
            model_config = llm_config.config

            llm_instance = llm_factory(provider, model, model_config, max_retries, retry_backoff)
            self.agents.get_agent(agent).set_llm(llm_instance)

    def __get_retry_settings(self, provider_config: ProviderConfig, default_config: DefaultConfig) -> Tuple[int, float]:
        """
        Helper method to extract retry settings for LLM configuration.

        Args:
            provider_config: Provider-specific configuration.
            default_config: Default configuration values.

        Returns:
            Tuple[int, float]: max_retries and retry_backoff values.
        """
        max_retries = provider_config.setting.max_retries or default_config.max_retries
        retry_backoff = provider_config.setting.retry_backoff or default_config.retry_backoff
        return max_retries, retry_backoff
