from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

from pydantic import BaseModel, Field, field_validator

from llms import LLM, llm_factory
from utils.decorators import auto_repr
from utils.yaml_utils import read_yaml

# Supported LLMs categorized by provider
SUPPORTED_LLMS = {
    'openai': [
        'chatgpt-4o-latest',
        'gpt-4o-2024-11-20',
        'gpt-4o-2024-08-06',
        'gpt-4o-2024-05-13',
        'o1-preview-2024-09-12',
        'o1-mini-2024-09-12',
        'gpt-3.5-turbo',
        'o3-mini'
    ],
    'ollama': [
        'llama3'
    ],
    'anthropic': [
        'claude-3-5-sonnet-20240620',
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


class LLMSettings(BaseModel):
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


class ProviderModelSettings(BaseModel):
    """Configuration for a specific provider's model."""
    
    name: str
    description: str
    api_key: str = Field(required=False, default=None)


class ProviderConnectionSettings(BaseModel):
    """Settings for a provider."""
    
    api_key: str = Field(required=False, default=None)
    max_retries: int = Field(ge=1, required=False, default=None)
    retry_backoff: int  = Field(ge=0, required=False, default=None)


class ProviderSettings(BaseModel):
    """Configuration for a specific provider."""

    name: str
    setting: ProviderConnectionSettings = Field(default=None)
    models: dict[str, ProviderModelSettings] = Field(default=None)

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


class AgentSettings(BaseModel):
    """Configuration for an agent."""

    description: str
    llm_config: LLMSettings = Field(required=False, default=None)


class RAGAgentSettings(BaseModel):
    """Configuration for an agent."""

    description: str
    vector_database_path: str
    collection_name: str
    llm_config: LLMSettings = Field(required=False, default=None)

    @field_validator('vector_database_path', mode='before')
    def valid_vector_database_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("vector_database_path must not be empty.")
        path = Path(v)
        if not path.exists():
            raise ValueError(f"vector_database_path '{v}' does not exist.")
        if not path.is_dir():
            raise ValueError(f"vector_database_path '{v}' is not a directory.")
        return v

    @field_validator('collection_name',  mode='before')
    def non_empty_collection_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("collection_name must not be empty.")
        return v


class DefaultSettings(BaseModel):
    """Default configuration settings for the project."""
    
    llm_config: LLMSettings
    max_retries: int = Field(ge=1, required=True)
    retry_backoff: int = Field(ge=0, required=True)
    max_graph_recursion_limit: Optional[int] = Field(ge=1, required=True)


class GenpodSettings(BaseModel):
    """Configuration for the Genpod project."""
    
    default: DefaultSettings
    providers: Dict[str, ProviderSettings]
    agents: Dict[str, AgentSettings]
    rag_agents: Dict[str, RAGAgentSettings]
    max_graph_recursion_limit: Optional[int] = Field(
        ge=1, 
        required=False, 
        default=None
    )


@dataclass
class AgentInfo:
    """
    Encapsulates configuration information for an agent.

    Attributes:
        agent_name (str): The human-readable name of the agent.
        agent_id (str): A unique identifier for the agent.
        alias (str): An optional alias for referencing the agent (default is an empty string).
        description (str): An optional description outlining the agent's role or functionality.
        llm (Optional[LLM]): The language model (LLM) instance associated with the agent, if applicable.
        recursion_limit (int): The maximum recursion depth allowed for tasks handled by the agent.
        use_rag (bool): A flag indicating whether retrieval-augmented generation (RAG) is enabled.
    """
    agent_name: str
    agent_id: str
    alias: str = ""
    description: str = ""
    llm: Optional[LLM] = None
    recursion_limit: int = 0
    use_rag: bool = False


@dataclass
class RAGAgentInfo:
    """
    Configuration information for a Retrieval-Augmented Generation (RAG) agent.

    Attributes:
        agent_name (str): The human-readable name of the RAG agent.
        agent_id (str): A unique identifier for the agent.
        alias (str): An optional alias for referencing the agent.
        description (str): A description outlining the agent's role and functionality.
        vector_database_path (str): The connection string or file system path for the vector database.
        collection_name (str): The name of the collection within the vector database.
        llm (Optional[LLM]): The associated language model (LLM) instance, if applicable.
        recursion_limit (int): The maximum recursion depth allowed for tasks handled by the agent.
    """
    agent_name: str
    agent_id: str
    alias: str = ""
    description: str = ""
    vector_database_path: str = ""
    collection_name: str = ""
    llm: Optional[LLM] = None
    recursion_limit: int = 0


class AgentRegistry(Enum):
    """
    Enum representing configuration for all project agents.
    Each member is an AgentInfo instance detailing an agent's role, settings, and behavior.
    """

    supervisor: AgentInfo = AgentInfo(
        agent_name="Project Supervisor",
        agent_id="SUP_01",
        alias="supervisor",
        description=(
            "Oversees the entire project workflow by coordinating the GenPod team. "
            "Delegates tasks such as transforming user prompts into requirements documents, "
            "generating deliverables/tasks, developing code/projects, and ensuring thorough reviews. "
            "Guides iterative cycles until the reviewer yields zero issues."
        ),
        recursion_limit=25,
        use_rag=False
    )

    architect: AgentInfo = AgentInfo(
        agent_name="Solution Architect", 
        agent_id="ARC_02",
        alias="architect",
        description=(
            "Generates a detailed, comprehensive requirements document and outlines deliverable/tasks based on the user prompt, "
            "laying the foundation for the project's architectural framework."
        ),
        recursion_limit=25,
        use_rag=True
    )

    coder: AgentInfo = AgentInfo(
        agent_name="Software Engineer", 
        agent_id="ENG_03",
        alias="coder",
        description=(
            "Executes assigned tasks by generating code with proper license headers, "
            "ensuring adherence to coding standards and project requirements."
        ),
        recursion_limit=25,
        use_rag=False
    )

    planner: AgentInfo = AgentInfo(
        agent_name="Project Planner", 
        agent_id="PLN_05",
        alias="planner",
        description=(
            "Transforms raw tasks or deliverables from the architect into detailed, actionable subtasks, "
            "and similarly refines issues identified by the reviewer into manageable tasks for execution."
        ),
        recursion_limit=25,
        use_rag=True
    )

    tests_generator: AgentInfo = AgentInfo(
        agent_name="Unit Tester", 
        agent_id="TST_06",
        alias="tests_generator",
        description=(
            "Prior to coding, generates detailed unit test cases and function signatures from the assigned tasks. "
            "These artifacts guide the Software Engineer in implementing functionality that meets quality and specification standards."
        ),
        recursion_limit=25,
        use_rag=False
    )

    reviewer: AgentInfo = AgentInfo(
        agent_name="Code Reviewer",
        agent_id="REV_09",
        alias="reviewer",
        description=(
            "Evaluates the generated project by reviewing code quality, clean code principles, naming conventions, "
            "and compliance with both internal and external standards. After reviewing, compiles and reports issues "
            "that need resolution before final project approval."
        ),
        recursion_limit=25,
        use_rag=False
    )

    rag_middleware: AgentInfo = AgentInfo(
        agent_name="RAG Middleware", 
        agent_id="RAG_MW_07",
        alias="rag_middleware",
        description=(
            "Acts as a mediator for the Retrieval-Augmented Generation (RAG) process by maintaining a group of specialized RAG agents. "
            "Upon receiving a question, it determines the most suitable agent to address it, forwards the question, and returns the accurate answer provided."
        ),
        recursion_limit=25,
        use_rag=False
    )

    research: AgentInfo = AgentInfo(
        agent_name="Research Assistant",
        agent_id="RES_08",
        alias="research",
        description=(
            "Conducts in-depth research by aggregating and synthesizing information from various online sources. "
            "Supports the project by refining queries, gathering relevant data, and generating insights that complement "
            "the work of other agents."
        ),
        recursion_limit=25,
        use_rag=False
    )

    @property
    def agent_name(self) -> str:
        return self.value.agent_name

    @property
    def agent_id(self) -> str:
        return self.value.agent_id

    @property
    def alias(self) -> str:
        return self.value.alias

    @property
    def description(self) -> str:
        return self.value.description

    @property
    def llm(self) -> Optional["LLM"]:
        return self.value.llm

    @property
    def recursion_limit(self) -> int:
        return self.value.recursion_limit

    @property
    def use_rag(self) -> bool:
        return self.value.use_rag
 
    @classmethod
    def get_agent(cls, alias: str) -> AgentInfo:
        """
        Retrieve an agent's information by its alias.

        Args:
            alias (str): The alias of the agent.

        Returns:
            AgentInfo: The corresponding AgentInfo object.
        """

        return cls[alias].value
    
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
    
    def __iter__(self) -> Iterator[AgentInfo]:
        """
        Custom iterator to return each enum member's agent info.

        Yields:
            AgentInfo: Yields each AgentInfo object from the enum.
        """
        for agent in AgentRegistry:
            yield agent.value


class RAGAgentRegistry(Enum):
    """
    Enum representing the configuration for specialized RAG agents.
    Each member is an instance of RAGAgentInfo tailored to handle specific Retrieval-Augmented Generation queries.
    """
    mismo_3_6_rag: RAGAgentInfo = RAGAgentInfo(
        agent_name="MISMO 3.6 RAG Agent", 
        agent_id="M3R_01",
        alias="mismo_3_6_rag",
        description=(
            "Specialized RAG agent that addresses queries related to MISMO 3.6 standards, providing accurate and comprehensive responses."
        ),
        recursion_limit=25
    )

    @property
    def agent_name(self) -> str:
        return self.value.agent_name

    @property
    def agent_id(self) -> str:
        return self.value.agent_id

    @property
    def alias(self) -> str:
        return self.value.alias

    @property
    def description(self) -> str:
        return self.value.description

    @property
    def llm(self) -> Optional["LLM"]:
        return self.value.llm

    @property
    def recursion_limit(self) -> int:
        return self.value.recursion_limit

    @property
    def vector_database_path(self) -> str:
        return self.value.vector_database_path

    @property
    def collection_name(self) -> str:
        return self.value.collection_name

    @classmethod
    def get_agent(cls, alias: str) -> RAGAgentInfo:
        """
        Retrieve a RAG agent's configuration by its alias.

        Args:
            alias (str): The alias of the agent.

        Returns:
            RAGAgentInfo: The corresponding RAGAgentInfo object.
        """
        return cls[alias].value

    @classmethod
    def get_agent_by_id(cls, agent_id: str) -> Optional[RAGAgentInfo]:
        """
        Retrieve a RAG agent's configuration by its unique identifier.

        Args:
            agent_id (str): The unique identifier of the agent.

        Returns:
            Optional[RAGAgentInfo]: The corresponding RAGAgentInfo object if found; otherwise, None.
        """
        for agent in cls:
            if agent.value.agent_id == agent_id:
                return agent.value
        return None

    @classmethod
    def has_agent(cls, alias: str) -> bool:
        """
        Check if a RAG agent with the specified alias exists.

        Args:
            alias (str): The alias of the agent.

        Returns:
            bool: True if the agent exists, False otherwise.
        """
        return any(agent.alias == alias for agent in cls)

    def __iter__(self) -> Iterator[RAGAgentInfo]:
        """
        Custom iterator to yield each RAG agent's configuration.

        Yields:
            RAGAgentInfo: Each RAGAgentInfo object stored in the enum.
        """
        for agent in RAGAgentRegistry:
            yield agent.value


@auto_repr
class ProjectConfig:
    """
    Configuration for the entire project, including agent configurations and vector database settings.
    """

    agents: AgentRegistry
    rag_agents: RAGAgentRegistry
    max_graph_recursion_limit: int
    __config_path: str
    __genpod_config: GenpodSettings

    def __init__(self, config_path: str) -> None:
        """
        Initializes the project configuration with predefined agents, their configurations,
        and vector database collection paths.
        """

        self.agents = AgentRegistry
        self.rag_agents = RAGAgentRegistry
        self.max_graph_recursion_limit = -1
        self.__config_path = config_path

    def load_config(self) -> None:
        """
        Loads the configuration data from a YAML file and updates the project settings accordingly.
        
        This method reads the YAML configuration from the file path specified during initialization, 
        parses the configuration into the internal `GenpodSettings` structure, and applies the configurations 
        by calling the appropriate update methods.
        """
        try:
            __yaml_data =  read_yaml(self.__config_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {self.__config_path}.")
        except Exception as e:
            raise ValueError(f"Error parsing YAML config: {e}")
    
        self.__genpod_config = GenpodSettings(**__yaml_data)
        self.__update_config()

    def __update_config(self) -> None:
        """
        Updates the project settings based on the loaded configuration data.
        """

        self.__set__max_graph_recursion_limit()
        self.__update__agents()
        self.__update__rag_agents()
        
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
                raise ValueError(f"Agent {agent} not found in {self.agents.__class__}.")

            llm_config = config.llm_config or self.__genpod_config.default.llm_config
            provider_config = self.__genpod_config.providers[llm_config.provider]
            max_retries, retry_backoff = self.__get_retry_settings(provider_config, self.__genpod_config.default)

            provider = llm_config.provider
            model = llm_config.model
            model_config = llm_config.config

            llm_instance = llm_factory(provider, model, model_config, max_retries, retry_backoff)
            self.agents.get_agent(agent).llm = llm_instance

    def __update__rag_agents(self) -> None:
        """
        Sets LLM instances and updates collection name and vector database path for RAG agents
        based on the loaded configuration.
        """
        for agent_alias, config in self.__genpod_config.rag_agents.items():
            if not self.rag_agents.has_agent(agent_alias):
                raise ValueError(f"RAG Agent '{agent_alias}' not found in {self.rag_agents.__class__.__name__}.")

            rag_agent = self.rag_agents.get_agent(agent_alias)

            llm_config = config.llm_config or self.__genpod_config.default.llm_config

            provider_config = self.__genpod_config.providers[llm_config.provider]

            max_retries, retry_backoff = self.__get_retry_settings(provider_config, self.__genpod_config.default)

            provider = llm_config.provider
            model = llm_config.model
            model_config = llm_config.config

            llm_instance = llm_factory(provider, model, model_config, max_retries, retry_backoff)

            rag_agent.llm = llm_instance
            rag_agent.collection_name = config.collection_name
            rag_agent.vector_database_path = config.vector_database_path

    def __get_retry_settings(self, provider_config: ProviderSettings, default_config: DefaultSettings) -> Tuple[int, float]:
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
