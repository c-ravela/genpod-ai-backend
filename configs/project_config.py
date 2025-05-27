import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from llms import LLM, llm_factory
from utils.decorators import auto_repr
from utils.yaml_utils import read_yaml

from models.rag_types import RAGType

# Supported LLMs categorized by provider
SUPPORTED_LLMS = {
    "openai": [
        "chatgpt-4o-latest",
        "gpt-4o-2024-11-20",
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-05-13",
        "o1-preview-2024-09-12",
        "o1-mini-2024-09-12",
        "gpt-3.5-turbo",
        "o3-mini",
    ],
    "ollama": ["llama3"],
    "anthropic": [
        "claude-3-5-sonnet-20240620",
        "claude-3-5-sonnet-20241022",
        "claude-3-7-sonnet-20250219",
        "claude-instant-1.2",
    ],
    "google": [
        "gemini-2.5-pro-preview-05-06",
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite"
    ]
}

def check_provider(provider: str) -> None:
    """
    Validate that the given provider string exists in SUPPORTED_LLMS.
    
    Args:
        provider: Name of the LLM provider to check.
    
    Raises:
        ValueError: If the provider is not supported.
    """
    if provider not in SUPPORTED_LLMS:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers are: {list(SUPPORTED_LLMS.keys())}"
        )

def check_model(provider: str, model: str) -> None:
    """
    Validate that the given model exists under the specified provider.
    
    Args:
        provider: Name of the LLM provider.
        model: Name of the model to check.
    
    Raises:
        ValueError: If the provider is unknown or the model is not supported.
    """
    if provider not in SUPPORTED_LLMS:
        raise ValueError(f"Unknown provider: {provider}")
    if model not in SUPPORTED_LLMS[provider]:
        raise ValueError(
            f"Unsupported model: {model} for provider {provider}. "
            f"Supported models are: {SUPPORTED_LLMS[provider]}"
        )


class LLMSettings(BaseModel):
    """
    Pydantic model for LLM configuration, including provider, model, and model-specific settings.
    """
    provider: str
    model: str
    config: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider")
    def _validate_provider(cls, v):
        """
        Field validator to ensure provider is supported.
        """
        check_provider(v)
        return v

    @field_validator("model")
    def _validate_model(cls, v, info):
        """
        Field validator to ensure model is supported for the selected provider.
        """
        provider = info.data.get("provider")
        check_model(provider, v)
        return v


class ProviderModelSettings(BaseModel):
    """
    Configuration for a specific model under a provider, including a description
    and optional override for api_key.
    """
    description: str
    api_key: Optional[str] = None


class ProviderConnectionSettings(BaseModel):
    """
    Connection-level settings for a provider, including default api_key and retry behavior.
    """
    api_key: Optional[str] = None
    max_retries: Optional[int] = Field(default=None, ge=1)
    retry_backoff: Optional[int] = Field(default=None, ge=0)


class ProviderSettings(BaseModel):
    """
    Aggregated provider settings, combining connection settings and per-model metadata.
    """
    setting: ProviderConnectionSettings = Field(default_factory=ProviderConnectionSettings)
    models: Dict[str, ProviderModelSettings] = Field(default_factory=dict)


class AgentSettings(BaseModel):
    """
    Per-agent configuration, including description and optional LLM override.
    """
    description: str
    llm_config: Optional[LLMSettings] = None


class RAGAgentSettings(BaseModel):
    """
    Configuration for a RAG agent:

      • which workflow variant (langchain_vector vs. llama_index)
      • where its vector DB lives
      • which collection to query
      • graph recursion depth
      • optional override of its LLM settings
      • for llama_index only: path to the retriever config file
    """
    description: str
    rag_type: RAGType

    vector_database_path: Path

    collection_name: str
    recursion_limit: int = Field(
        default=5000,
        ge=1,
        description="Max graph recursion limit for this RAG agent"
    )

    llm_config: Optional[LLMSettings] = None
    config_path: Optional[Path] = None

    @field_validator("vector_database_path", mode="before")
    def _check_persist_dir(cls, v):
        p = Path(v)
        if not p.exists() or not p.is_dir():
            raise ValueError(f"vector_database_path '{v}' does not exist or is not a directory.")
        return p

    @field_validator("collection_name", mode="before")
    def _check_collection(cls, v):
        if not v.strip():
            raise ValueError("collection_name must not be empty.")
        return v

    @field_validator("config_path", mode="before")
    def _check_config_path_exists(cls, v):
        # allow None here; presence enforced in model_validator
        if v is None:
            return None
        p = Path(v)
        if not p.exists() or not p.is_file():
            raise ValueError(f"config_path '{v}' does not exist or is not a file.")
        return p

    @model_validator(mode="after")
    def _require_config_for_llama_index(cls, model: "RAGAgentSettings") -> "RAGAgentSettings":
        """
        Enforce that `config_path` is provided when using the llama_index workflow.
        """

        if model.rag_type == RAGType.LLAMA_INDEX and model.config_path is None:
            raise ValueError("`config_path` is required for rag_type='llama_index'")
        return model


class DefaultSettings(BaseModel):
    """
    Default fallbacks for LLM settings, retries, backoff, and graph recursion limit.
    """
    llm_config: LLMSettings
    max_retries: int = Field(ge=1)
    retry_backoff: int = Field(ge=0)
    max_graph_recursion_limit: Optional[int] = Field(ge=1)


class GenpodSettings(BaseModel):
    """
    Top-level Pydantic schema for the entire Genpod configuration.
    """
    default: DefaultSettings
    providers: Dict[str, ProviderSettings]
    agents: Dict[str, AgentSettings]
    rag_agents: Dict[str, RAGAgentSettings] = Field(default_factory=dict)
    max_graph_recursion_limit: Optional[int] = Field(default=None, ge=1)


@dataclass
class AgentInfo:
    """
    Holds runtime configuration and state for a standard agent.
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
    Holds runtime configuration and state for a dynamically loaded RAG agent.
    """
    agent_name: str
    agent_id: str
    rag_type: RAGType

    alias: str = ""
    description: str = ""

    # Where the vector DB is persisted (for both pipelines)
    vector_database_path: str = ""
    collection_name: str = ""

    # How deep the state‐graph may recurse
    recursion_limit: int = 5000

    # Only used by llama_index agents (must be a valid file path then)
    config_path: Optional[str] = None

    # Populated later via llm_factory
    llm: Optional[LLM] = None


class AgentRegistry:
    """
    Registry of builtin AgentInfo definitions for standard agents.
    Instantiate once and access agents as attributes, e.g. registry.supervisor.
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
        recursion_limit=5000,
        use_rag=False,
    )
    architect: AgentInfo = AgentInfo(
        agent_name="Solution Architect",
        agent_id="ARC_02",
        alias="architect",
        description=(
            "Generates a detailed, comprehensive requirements document and outlines deliverable/tasks "
            "based on the user prompt, laying the foundation for the project's architectural framework."
        ),
        recursion_limit=5000,
        use_rag=True,
    )
    coder: AgentInfo = AgentInfo(
        agent_name="Software Engineer",
        agent_id="ENG_03",
        alias="coder",
        description=(
            "Executes assigned tasks by generating code with proper license headers, "
            "ensuring adherence to coding standards and project requirements."
        ),
        recursion_limit=3000,
        use_rag=False,
    )
    planner: AgentInfo = AgentInfo(
        agent_name="Project Planner",
        agent_id="PLN_05",
        alias="planner",
        description=(
            "Transforms raw tasks or deliverables from the architect into detailed, actionable subtasks, "
            "and similarly refines issues identified by the reviewer into manageable tasks for execution."
        ),
        recursion_limit=5000,
        use_rag=True,
    )
    tests_generator: AgentInfo = AgentInfo(
        agent_name="Unit Tester",
        agent_id="TST_06",
        alias="tests_generator",
        description=(
            "Prior to coding, generates detailed unit test cases and function signatures from the assigned tasks. "
            "These artifacts guide the Software Engineer in implementing functionality that meets quality and specification standards."
        ),
        recursion_limit=3000,
        use_rag=False,
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
        recursion_limit=3000,
        use_rag=False,
    )
    rag_middleware: AgentInfo = AgentInfo(
        agent_name="RAG Middleware",
        agent_id="RAG_MW_07",
        alias="rag_middleware",
        description=(
            "Acts as a mediator for the Retrieval-Augmented Generation (RAG) process by maintaining a group of specialized RAG agents. "
            "Upon receiving a question, it determines the most suitable agent to address it, forwards the question, and returns the accurate answer provided."
        ),
        recursion_limit=5000,
        use_rag=False,
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
        recursion_limit=3000,
        use_rag=False,
    )

    @classmethod
    def values(cls) -> Iterator[AgentInfo]:
        """Yield all AgentInfo instances in the registry."""
        for attr in (
            "supervisor", "architect", "coder", "planner",
            "tests_generator", "reviewer", "rag_middleware", "research"
        ):
            yield getattr(cls, attr)

    @classmethod
    def has_agent(cls, alias: str) -> bool:
        """Return True if an AgentInfo with the given alias exists."""
        return any(a.alias == alias for a in cls.values())

    @classmethod
    def get_agent(cls, alias: str) -> AgentInfo:
        """Return the AgentInfo matching the alias, or raise KeyError."""
        for a in cls.values():
            if a.alias == alias:
                return a
        raise KeyError(f"No agent with alias={alias!r}")


@auto_repr
class ProjectConfig:
    """
    Main entrypoint for loading and applying Genpod project configuration.
    Reads a YAML file, resolves environment-variable placeholders,
    validates via Pydantic, and instantiates LLMs for both standard and RAG agents.
    """

    def __init__(self, config_path: str) -> None:
        """
        Initialize the ProjectConfig.

        Args:
            config_path: Path to the Genpod YAML configuration file.
        """
        self._config_path = config_path
        self.agents = AgentRegistry
        self.rag_agents: Dict[str, RAGAgentInfo] = {}
        self.max_graph_recursion_limit: int = -1
        self._settings: Optional[GenpodSettings] = None

    def load_config(self) -> None:
        """
        Load, preprocess, validate, and apply the YAML configuration.
        """
        raw = read_yaml(self._config_path)
        raw = self._resolve_env_vars(raw)
        self._settings = GenpodSettings(**raw)
        self._apply(self._settings)

    def _resolve_env_vars(self, raw: dict) -> dict:
        """
        Replace any "$ENV_VAR" strings in provider/model api_key fields with actual
        environment variable values. Leaves None if the variable is unset.
        """
        for prov in raw.get("providers", {}).values():
            api = prov["setting"].get("api_key")
            if isinstance(api, str) and api.startswith("$"):
                prov["setting"]["api_key"] = os.getenv(api[1:], None)
            for m in prov["models"].values():
                key = m.get("api_key")
                if isinstance(key, str) and key.startswith("$"):
                    m["api_key"] = os.getenv(key[1:], None)
        return raw

    def _apply(self, cfg: GenpodSettings) -> None:
        """
        Apply the parsed GenpodSettings to configure max recursion limit and
        instantiate all agent and RAGAgent LLMs.
        """
        self._set_max_graph_limit(cfg)
        self._update_agents(cfg)
        self._update_rag_agents(cfg)

    def _set_max_graph_limit(self, cfg: GenpodSettings) -> None:
        """
        Set the global max_graph_recursion_limit from top-level or default.
        """
        self.max_graph_recursion_limit = (
            cfg.max_graph_recursion_limit
            if cfg.max_graph_recursion_limit is not None
            else cfg.default.max_graph_recursion_limit  # type: ignore
        )

    def _get_retry_settings(
        self, prov: ProviderSettings, default: DefaultSettings
    ) -> Tuple[int, int]:
        """
        Determine retry settings (max_retries, retry_backoff) for a provider.
        """
        return (
            prov.setting.max_retries or default.max_retries,
            prov.setting.retry_backoff or default.retry_backoff,
        )

    def _update_agents(self, cfg: GenpodSettings) -> None:
        """
        Instantiate and assign LLMs for each registered standard agent.
        Warn if no api_key is provided at either model or provider level.
        """
        for alias, agent_cfg in cfg.agents.items():
            if not self.agents.has_agent(alias):
                raise ValueError(f"Unknown agent alias {alias!r}")

            llm_cfg = agent_cfg.llm_config or cfg.default.llm_config  # type: ignore

            # re-validate provider/model
            check_provider(llm_cfg.provider)
            check_model(llm_cfg.provider, llm_cfg.model)

            prov = cfg.providers[llm_cfg.provider]
            mr, rb = self._get_retry_settings(prov, cfg.default)

            model_meta = prov.models[llm_cfg.model]
            api_key = model_meta.api_key or prov.setting.api_key

            if api_key is None:
                warnings.warn(
                    f"[config] No API key found for provider='{llm_cfg.provider}', "
                    f"model='{llm_cfg.model}' (agent='{alias}'); "
                    f"please recheck '{self._config_path}' to ensure a valid api_key or "
                    "environment variable is provided.",
                    UserWarning,
                )


            full_cfg = {**llm_cfg.config, "api_key": api_key}
            inst = llm_factory(llm_cfg.provider, llm_cfg.model, full_cfg, mr, rb)
            self.agents.get_agent(alias).llm = inst

    def _update_rag_agents(self, cfg: GenpodSettings) -> None:
        """
        Dynamically instantiate and assign LLMs for each RAG agent defined in the config.
        Warn if no api_key is provided at either model or provider level.
        """
        for alias, rag_cfg in cfg.rag_agents.items():
            rag = RAGAgentInfo(
                agent_name       = alias,
                agent_id         = alias,
                alias            = alias,
                description      = rag_cfg.description,
                rag_type         = rag_cfg.rag_type,
                vector_database_path = str(rag_cfg.vector_database_path),
                collection_name  = rag_cfg.collection_name,
                recursion_limit  = rag_cfg.recursion_limit,
                config_path      = str(rag_cfg.config_path) if rag_cfg.config_path else None,
            )

            llm_cfg = rag_cfg.llm_config or cfg.default.llm_config  # type: ignore
            check_provider(llm_cfg.provider)
            check_model(llm_cfg.provider, llm_cfg.model)

            prov = cfg.providers[llm_cfg.provider]
            mr, rb = self._get_retry_settings(prov, cfg.default)

            model_meta = prov.models[llm_cfg.model]
            api_key = model_meta.api_key or prov.setting.api_key

            if api_key is None:
                warnings.warn(
                    f"[config] No API key found for provider='{llm_cfg.provider}', "
                    f"model='{llm_cfg.model}' (agent='{alias}'); "
                    f"please recheck '{self._config_path}' to ensure a valid api_key or "
                    "environment variable is provided.",
                    UserWarning,
                )


            full_cfg = {**llm_cfg.config, "api_key": api_key}
            inst = llm_factory(llm_cfg.provider, llm_cfg.model, full_cfg, mr, rb)
            rag.llm = inst

            self.rag_agents[alias] = rag
