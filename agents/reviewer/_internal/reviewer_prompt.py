from os import getcwd, path

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from core.prompt import Prompt, PromptTemplateAdapter
from models import IssuesReport
from utils.logs.logging_utils import logger
from utils.yaml_utils import read_yaml

REVIEWER_PROMPTS_PATH = path.join(getcwd(), "prompts", "reviewer_prompts.yaml")


class ReviewerPrompts:
    """
    Manages and provides prompt templates for code review.

    This class loads prompt templates from a YAML configuration file and initializes
    specific prompt instances. Currently, it supports generating a static code analysis prompt.

    Attributes:
        use_rag (bool): Flag indicating whether to use Retrieval-Augmented Generation (RAG).
        static_code_analysis_prompt (Prompt): A prompt instance for static code analysis.
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
