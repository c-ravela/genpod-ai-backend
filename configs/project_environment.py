import os
from typing import Any, Union

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


class MandatoryValueNotFound(Exception):
    """Exception raised when a mandatory environment variable is not found."""
    def __init__(self, var_name):
        self.message = f"Mandatory environment variable '{var_name}' not found."
        super().__init__(self.message)

class InvalidPathError(Exception):
    """Exception raised when the provided path does not exist."""
    def __init__(self, var_name, path):
        self.message = f"Invalid path for '{var_name}': '{path}' does not exist."
        super().__init__(self.message)

class InvalidYAMLError(Exception):
    """Exception raised when the provided file is not a valid YAML file."""
    def __init__(self, var_name, path):
        self.message = f"The file at '{path}' specified by '{var_name}' is not a valid YAML file."
        super().__init__(self.message)

class EnvironmentVariables(BaseModel):
    """Model representing required environment variables for the project."""

    GENPOD_CONFIG_PATH: str = Field(
        description="Path for Genpod configuration file.",
        required=True,
    )

    OPENAI_API_KEY: str = Field(
        description="API key for OpenAI services.",
        required=False,
    )

    SEMGREP_APP_TOKEN: str = Field(
        description="App token for Semgrep service.",
        required=False,
    )

    @field_validator('GENPOD_CONFIG_PATH')
    def check_GENPOD_CONFIG_PATH(cls, v: str) -> str:
        """Validate if the GENPOD_CONFIG_PATH exists and is a valid YAML file.

        Args:
            cls: The class being validated.
            v: The value of the GENPOD_CONFIG_PATH.

        Raises:
            InvalidPathError: If the path does not exist.
            InvalidYAMLError: If the file is not a valid YAML file.

        Returns:
            str: The validated path.
        """
        if not os.path.exists(v):
            raise InvalidPathError("GENPOD_CONFIG_PATH", v)

        try:
            with open(v, 'r') as file:
                yaml.safe_load(file)
        except yaml.YAMLError:
            raise InvalidYAMLError("GENPOD_CONFIG_PATH", v)

        return v

class ProjectEnvironment:
    """Class to manage and validate the project's environment variables."""

    REQUIRED_ENV_VARS = EnvironmentVariables.model_fields.keys()

    def __init__(self):
        """Initialize the ProjectEnvironment by loading and validating environment variables."""
        self.env_variables = self.load_env_variables()

    def load_env_variables(self) -> dict:
        """Load and validate all required environment variables.

        Raises:
            MandatoryValueNotFound: If any required environment variable is missing.
            Exception: If any validation errors occur.

        Returns:
            dict: A dictionary of validated environment variables.
        """
        env_data = {var: os.getenv(var) for var in self.REQUIRED_ENV_VARS}
        
        for var in self.REQUIRED_ENV_VARS:
            if env_data[var] is None:
                raise MandatoryValueNotFound(var)

        try:
            return EnvironmentVariables(**env_data).model_dump()
        except ValidationError as e:
            raise Exception(f"Environment validation failed: {e}")

    def get_validated_env_variables(self) -> dict:
        """Return all validated environment variables.

        Returns:
            dict: A dictionary of validated environment variables.
        """
        return self.env_variables
    
    def get_env(self, name: str) -> Union[Any, None]:
        """Retrieve the value of a specific environment variable.

        Args:
            name (str): The name of the environment variable to retrieve.

        Returns:
            Any: The value of the environment variable if it exists.
            None: If the environment variable is not found.
        """
        return self.env_variables.get(name, None)
