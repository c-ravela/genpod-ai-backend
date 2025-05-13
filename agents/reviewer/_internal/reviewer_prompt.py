from os import getcwd, path

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from core.prompt import Prompt, PromptTemplateAdapter
from models import (DockerfileSelectionResponse, DockerSandboxExecutorParams,
                    IssuesReport, LanguageSelectionResponse)
from utils.logger import logger
from utils.yaml_utils import read_yaml

REVIEWER_PROMPTS_PATH = path.join(getcwd(), "prompts", "reviewer_prompts.yaml")


class ReviewerPrompts:
    """
    Manages and provides prompt templates for code review.

    This class loads prompt templates from a YAML configuration file and initializes
    specific prompt instances. Currently, it supports generating prompts for:
      - Static code analysis (producing IssuesReport).
      - Generic check issue reporting (producing IssuesReport).
      - Dockerfile selection (producing DockerfileSelectionResponse).
      - Docker sandbox executor parameters (producing DockerSandboxExecutorParams).

    Attributes:
        use_rag (bool): Flag indicating whether to use Retrieval-Augmented Generation (RAG).
        static_code_analysis_prompt (Prompt): A prompt instance for static code analysis.
        generic_check_issue_report_prompt (Prompt): A prompt instance for generating a generic IssuesReport.
        dockerfile_selection_prompt (Prompt): A prompt instance for selecting the appropriate Dockerfile.
        docker_sandbox_executor_prompt (Prompt): A prompt instance for generating parameters for Docker sandbox execution.
    """

    def __init__(self, use_rag: bool):
        """
        Initializes the ReviewerPrompts instance.

        Loads prompt templates from the YAML configuration and creates the static code
        analysis prompt template.

        Args:
            use_rag (bool): Flag indicating whether to use Retrieval-Augmented Generation (RAG).

        Raises:
            Exception: If the YAML configuration fails to load.
            KeyError: If the required prompt template key is missing in the configuration.
        """
        self.use_rag = use_rag

        try:
            self._template_from_yaml = read_yaml(REVIEWER_PROMPTS_PATH)
            logger.info("Successfully loaded prompt templates from %s", REVIEWER_PROMPTS_PATH)
        except Exception as e:
            logger.error("Failed to load architect prompt configuration from %s: %s", REVIEWER_PROMPTS_PATH, e)
            raise
        
        static_code_analysis_prompt_template = PromptTemplate(
            template=self.get_template('static_code_analysis_prompt_template'),
            input_variables= ['static_analysis_tool', 'tool_result', 'error_message'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=IssuesReport
                ).get_format_instructions()
            }
        )

        self.static_code_analysis_prompt = Prompt(
            adapter=PromptTemplateAdapter(static_code_analysis_prompt_template)
        )

        generic_check_issue_report_prompt_template = PromptTemplate(
            template=self.get_template('generic_check_issue_report_prompt_template'),
            input_variables=['check_name', 'check_description', 'raw_check_output'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=IssuesReport
                ).get_format_instructions()
            }
        )
        self.generic_check_issue_report_prompt = Prompt(
            adapter=PromptTemplateAdapter(generic_check_issue_report_prompt_template)
        )

        # Dockerfile Selection Prompt
        dockerfile_selection_prompt_template = PromptTemplate(
            template=self.get_template('dockerfile_selection_prompt_template'),
            input_variables=['job_description', 'available_dockerfiles'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=DockerfileSelectionResponse
                ).get_format_instructions()
            }
        )
        self.dockerfile_selection_prompt = Prompt(
            adapter=PromptTemplateAdapter(dockerfile_selection_prompt_template)
        )

        # Docker Sandbox Executor Prompt
        docker_sandbox_executor_prompt_template = PromptTemplate(
            template=self.get_template('docker_sandbox_executor_prompt_template'),
            input_variables=['task_description', 'docker_image_description'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=DockerSandboxExecutorParams
                ).get_format_instructions()
            }
        )
        self.docker_sandbox_executor_prompt = Prompt(
            adapter=PromptTemplateAdapter(docker_sandbox_executor_prompt_template)
        )

        language_selection_prompt_template = PromptTemplate(
            template=self.get_template('language_selection_prompt_template'),
            input_variables=['requirements', 'available_languages'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=LanguageSelectionResponse
                ).get_format_instructions()
            }
        )
        self.language_selection_prompt = Prompt(
            adapter=PromptTemplateAdapter(language_selection_prompt_template)
        )

        file_path_selection_prompt_template = PromptTemplate(
            template=self.get_template('file_path_selection_prompt_template'),
            input_variables=[
                'check_name',
                'check_description',
                'project_directory',
                'directory_listing',
                'command',
                'command_description'
            ],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=LanguageSelectionResponse
                ).get_format_instructions()
            }
        )
        self.file_path_selection_prompt = Prompt(
            adapter=PromptTemplateAdapter(file_path_selection_prompt_template)
        )

    def get_template(self, key: str) -> str:
        """
        Retrieves the prompt template string for a given key from the YAML configuration.
        
        The YAML configuration is expected to have the following structure:
        
            {
                "<key>": {
                    "template": "<multi-line template string>",
                    ...
                },
                ...
            }
        
        Args:
            key (str): The key corresponding to the desired prompt template.
        
        Returns:
            str: The prompt template string for the given key.
        
        Raises:
            KeyError: If the key or the 'template' sub-key is not found.
        """
        try:
            template_str = self._template_from_yaml[key]['template']
            logger.debug("Retrieved template for key '%s': %s", key, template_str)
            return template_str
        except KeyError as e:
            logger.error("Key error: Could not find template for key '%s': %s", key, e)
            raise KeyError(f"Template for key '{key}' not found in the configuration.") from e
