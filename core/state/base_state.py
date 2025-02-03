
import os
from typing import List, Optional, Tuple

from pydantic import *

from models.constants import ChatRoles, PStatus
from models.models import Task
from utils.logs.logging_utils import logger


class ConfiguredBaseModel(BaseModel):
    """
    A base Pydantic model configured for strict validation and custom formatting.

    This model is designed as the foundation for all application-specific models.
    It enforces the following:
    
    - **Strict Field Validation:** Extra fields not defined in the model are forbidden.
      This is achieved via the model configuration (`extra='forbid'`), which helps in
      catching typos or unexpected input early in the validation process.
    
    - **Custom String Representation:** The `__str__` method is overridden to return
      a nicely formatted JSON representation of the model. This is useful for debugging
      and logging purposes, as it provides a clear and readable output of the model's data.
    """
    model_config = ConfigDict(extra='forbid')

    def __str__(self):
        return f"{self.__class__.__name__}({self.model_dump_json(indent=4)})"


class BaseInputState(ConfiguredBaseModel):
    """
    Represents the input state of an agent before processing a request.
    """

    user_prompt: str = Field(
        description="The user's original prompt for code generation."
    )
    project_status: PStatus = Field(
        description="The current status of the project."
    )
    project_directory: str = Field(
        description="The absolute path where the generated project will be saved."
    )
    current_task: Task = Field(
        description="The task that the agent is assigned to work on."
    )
    chat_history: List[Tuple[ChatRoles, str]] = Field(
        default_factory=list,
        description="A list of chat messages exchanged between the user and the agent.",
    )

    @field_validator('user_prompt')
    def user_prompt_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            logger.error("Validation error: user_prompt cannot be empty.")
            raise ValueError("user_prompt cannot be empty.")
        logger.debug("Validated user_prompt: '%s'", v)
        return v
    
    @field_validator('project_directory')
    def project_directory_must_be_absolute(cls, v: str) -> str:
        if not os.path.isabs(v):
            logger.error("Validation error: project_directory must be an absolute path. Received: %s", v)
            raise ValueError("project_directory must be an absolute path.")
        logger.debug("Validated project_directory: '%s'", v)
        return v
    
    @model_validator(mode="after")
    def check_inter_field_consistency(self) -> 'BaseInputState':
        """
        Validates that if project_status is not 'NONE', a non-empty user_prompt is provided.
        """
        logger.debug("Running inter-field consistency check for BaseInputState")
        if self.project_status != "NONE" and not self.user_prompt.strip():
            logger.error("Inter-field validation failed: When project_status is not 'NONE', user_prompt must be provided.")
            raise ValueError("When project_status is not 'NONE', user_prompt must be provided.")
        logger.debug("Inter-field consistency check passed for BaseInputState")
        return self


class BaseOutputState(ConfiguredBaseModel):
    """
    Represents the output state of an agent after processing a request.
    """
    current_task: Task = Field(
        description="The current task assigned to the agent."
    )
    chat_history: List[Tuple[ChatRoles, str]] = Field(
        default_factory=list,
        description="A list of chat messages exchanged between the user and the agent.",
    )


class BaseState(ConfiguredBaseModel):
    """
    Base class for agent states, holding shared attributes.
    """

    user_prompt: str = Field(
        default="",
        description="The user's original prompt for code generation."
    )
    project_status: PStatus = Field(
        default=PStatus.NONE,
        description="The current status of the project."
    )
    project_directory: str = Field(
        default="",
        description="The absolute path where the generated project will be saved."
    )
    current_task: Task = Field(
        default_factory=Task,
        description="The task that the agent is assigned to work on."
    )
    chat_history: List[Tuple[ChatRoles, str]] = Field(
        default_factory=list,
        description="A list of chat messages exchanged between the user and the agent.",
    )

    # Internal
    operational_mode: Optional[str] = Field(
        default=None,
        description="The current operational mode of the agent."
    )
    current_mode_stage: str = Field(
        default="",
        description="Represents the current operational stage of the agent. This field tracks the active phase in the agent's workflow, helping to manage state transitions and control mode-specific behavior internally."
    )
    last_node: Optional[str] = Field(
        default=None,
        description="The most recently visited node in the workflow."
    )
    active_node: Optional[str] = Field(
        default=None,
        description="The current active node in the workflow."
    )
    error_message: Optional[str] = Field(
        default=None,
        description="The most recent error message encountered by the agent."
    )
    error_count: int = Field(
        default=0,
        description="Total number of errors encountered since the agent started."
    )
