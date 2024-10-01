"""
Constants used by the project.
"""
import os
from dataclasses import dataclass
from enum import Enum, EnumType
from typing import Any, Dict, Union

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

load_dotenv()

def create_openai_chat_model_instance(
    model: str,
    temperature: float,
    max_retries: int,
    streaming: bool,
    model_kwargs: Dict[str, Any]
) -> ChatOpenAI:
    """
    Creates an instance of the ChatOpenAI model with the provided configuration.

    Args:
        model (str): The name of the OpenAI model to be used (e.g., 'gpt-3.5-turbo').
        temperature (float): Controls randomness in the model's output. A value between 0 and 1,
            where higher values (e.g., 0.9) result in more random outputs and lower values (e.g., 0.2) make the output more focused.
        max_retries (int): The number of retry attempts in case of failure during model execution.
        streaming (bool): Whether to enable streaming mode for the output (True) or not (False).
        model_kwargs (Dict[str, Any]): Additional keyword arguments for customizing the ChatOpenAI instance.

    Returns:
        ChatOpenAI: An initialized instance of the ChatOpenAI model configured with the provided parameters.

    Raises:
        ValueError: If an unsupported model is provided, or any argument is out of valid range.

    Example:
        chat_model = create_openai_chat_model_instance(
            model='gpt-3.5-turbo',
            temperature=0.7,
            max_retries=3,
            streaming=False,
            model_kwargs={'seed': 400}
        )
    """

    supported_openai_models = ['gpt-4-turbo', 'gpt-4o-2024-05-13', 'gpt-4o-2024-08-06', 'chatgpt-4o-latest', 'gpt-4o']

    if model not in supported_openai_models:
        raise ValueError(f"Unsupported model '{model}' provided for ChatOpenAI. Supported models are: {', '.join(supported_openai_models)}")

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_retries=max_retries,
        streaming=streaming,
        model_kwargs=model_kwargs
    )

def create_ollama_chat_model_instance(model: str, temperature: float, keep_alive: bool) -> ChatOllama:
    """
    Creates an instance of the ChatOllama model with the provided configuration.

    Args:
        model (str): The name of the Ollama model to be used (e.g., 'llama3').
        temperature (float): Controls randomness in the model's output. A value between 0 and 1,
            where higher values (e.g., 0.9) result in more random outputs, and lower values (e.g., 0.2) make the output more focused.
        keep_alive (bool): Whether to keep the session alive for reuse (True) or not (False).

    Returns:
        ChatOllama: An initialized instance of the ChatOllama model configured with the provided parameters.

    Raises:
        ValueError: If an unsupported model is provided.

    Example:
    chat_model = create_ollama_chat_model_instance(
        model='llama3',
        temperature=0.7,
        keep_alive=True
    )
    """

    supported_ollama_models = ["llama3"]

    if model not in supported_ollama_models:
        raise ValueError(f"Unsupported model '{model}' provided for ChatOllama. Supported models are: {', '.join(supported_ollama_models)}")

    return ChatOllama(
        model=model,
        temperature=temperature,
        keep_alive=keep_alive
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
    """

    agent_name: str
    agent_id: str
    alias: str = ""
    description: str = ""
   
class AgentConfig(AgentInfo):
    """
    Configuration for an agent, including its LLM settings and an optional thread ID.

    Attributes:
        agent_name (str): The name of the agent.
        agent_id (str): The unique identifier of the agent.
        llm (ChatOpenAI): The LLM instance associated with the agent.
        thread_id (Union[int, None]): Optional thread ID for the agent.
    """

    def __init__(self, agent_name: str, agent_id: str, chat_model: Union[ChatOpenAI, ChatOllama]) -> None:
        """
        Initializes the agent configuration with the given parameters.

        Args:
            agent_name (str): The name of the agent.
            agent_id (str): The unique identifier of the agent.
            llm_config (LLMConfig): The LLM configuration for this agent.
        """
        super().__init__(agent_name, agent_id)
        self.llm: Union[ChatOpenAI, ChatOllama] = chat_model
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
        tests_generator (GraphInfo): Information about the Unit Tester Graph.
        modernizer (GraphInfo): Information about the Knowledge Graph Generator Graph.
        reviewer (GraphInfo): Information about the Code Reviewer Graph.
    """
    supervisor = GraphInfo("Project Supervisor Graph", "GRPH_01_SUP")
    architect = GraphInfo("Solution Architect Graph", "GRPH_02_ARC")
    coder = GraphInfo("Software Engineer Graph", "GRPH_03_ENG")
    rag = GraphInfo("Document Repository Manager Graph", "GRPH_04_RAG")
    planner = GraphInfo("Project Planner Graph", "GRPH_05_PLN")
    tests_generator = GraphInfo("Unit Tester Graph", "GRPH_06_TST")
    modernizer = GraphInfo("Knowledge Graph Generator Graph", "GRPH_07_MOD")
    reviewer = GraphInfo("Code Reviewer Graph", "GRPH_08_REV")

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

    supervisor = AgentInfo(
        "Project Supervisor", 
        "SUP_01",
        alias="supervisor",
        description="Coordinates with the team, assigns tasks, and guides the team toward successful project completion."
    )

    architect = AgentInfo(
        "Solution Architect", 
        "ARC_02",
        alias="architect",
        description="Defines the project requirements and outlines the architectural framework."
    )

    coder = AgentInfo(
        "Software Engineer", 
        "ENG_03",
        alias="coder",
        description="Develops and writes code to the tasks assigned."
    )

    rag = AgentInfo(
        "Document Repository Manager", 
        "RAG_04",
        alias="rag",
        description="Oversees the vector database, manages document and file storage, and provides relevant information in response to queries."
    )

    planner = AgentInfo(
        "Project Planner", 
        "PLN_05",
        alias="planner",
        description="Creates detailed plans for task execution, based on requirements provided."
    )

    tests_generator = AgentInfo(
        "Unit Tester", 
        "TST_06",
        alias="tests_generator",
        description="Develops and executes unit test cases to ensure code quality and functionality."
    )

    modernizer = AgentInfo(
        "Knowledge Graph Generator", 
        "MOD_07",
        alias="modernizer",
        description="Generates and maintains the knowledge graph for the project, facilitating data relationships and insights."
    )

    human = AgentInfo(
        "Human Intervention Specialist", 
        "HUM_08",
        alias="human",
        description="Provides assistance and oversight when automated systems encounter issues or produce unreliable results."
    )

    reviewer = AgentInfo(
        "Code Reviewer",
        "REV_09",
        alias="reviwer",
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
    
AGENTS_CONFIG: Dict[str, AgentConfig] = {
    ProjectAgents.supervisor.agent_id: AgentConfig(
        ProjectAgents.supervisor.agent_name,
        ProjectAgents.supervisor.agent_id,
        create_ollama_chat_model_instance(
            model="llama3",
            temperature=0.4,
            keep_alive=True
        )
    ),
    ProjectAgents.architect.agent_id: AgentConfig(
        ProjectAgents.architect.agent_name,
        ProjectAgents.architect.agent_id,
        create_ollama_chat_model_instance(
            model="llama3",
            temperature=0.3,
            keep_alive=True
        )
    ),
    ProjectAgents.coder.agent_id: AgentConfig(
        ProjectAgents.coder.agent_name,
        ProjectAgents.coder.agent_id,
        create_ollama_chat_model_instance(
            model="llama3",
            temperature=0.3,
            keep_alive=True
        )
    ),
    ProjectAgents.rag.agent_id: AgentConfig(
        ProjectAgents.rag.agent_name,
        ProjectAgents.rag.agent_id,
        create_ollama_chat_model_instance(
            model="llama3",
            temperature=0,
            keep_alive=True
        )
    ),
    ProjectAgents.planner.agent_id: AgentConfig(
        ProjectAgents.planner.agent_name,
        ProjectAgents.planner.agent_id,
        create_ollama_chat_model_instance(
            model="llama3",
            temperature=0.2,
            keep_alive=True
        )
    ),
    ProjectAgents.tests_generator.agent_id: AgentConfig(
        ProjectAgents.tests_generator.agent_name,
        ProjectAgents.tests_generator.agent_id,
        create_ollama_chat_model_instance(
            model="llama3",
            temperature=0.4,
            keep_alive=True
        )
    ),
    ProjectAgents.modernizer.agent_id: AgentConfig(
        ProjectAgents.modernizer.agent_name,
        ProjectAgents.modernizer.agent_id,
        create_ollama_chat_model_instance(
            model="llama3",
            temperature=0.4,
            keep_alive=True
        )
    ),
    ProjectAgents.human.agent_id: AgentConfig(
        ProjectAgents.human.agent_name,
        ProjectAgents.human.agent_id,
        create_ollama_chat_model_instance(
            model="llama3",
            temperature=0.4,
            keep_alive=True
        )
    ),
    ProjectAgents.reviewer.agent_id: AgentConfig(
        ProjectAgents.reviewer.agent_name,
        ProjectAgents.reviewer.agent_id,
        create_ollama_chat_model_instance(
            model="llama3",
            temperature=0.4,
            keep_alive=True
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
        self.collection_name = "MISMO-version-3.6-docs"
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
