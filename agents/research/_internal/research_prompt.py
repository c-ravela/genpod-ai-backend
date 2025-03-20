from os import getcwd, path

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from core.prompt import Prompt, PromptTemplateAdapter
from models import (GeneratedResponse, RelevanceEvaluationResponse,
                    SourceSelectionResponse)
from utils.logger import logger
from utils.yaml_utils import read_yaml

RESEARCH_PROMPTS_PATH = path.join(getcwd(), "prompts", "research_prompts.yaml")


class ResearchPrompts:
    """
    A class to load and manage research prompt templates for source selection,
    relevance evaluation, and response generation from a YAML configuration file.

    The class reads a YAML file that contains prompt template definitions and uses
    them to instantiate prompt objects with proper formatting instructions based on
    Pydantic models.
    """
  
    def __init__(self):
        """
        Initializes the ResearchPrompts instance by loading the YAML configuration
        and setting up prompt templates for source selection, relevance checking, and
        response generation.

        Raises:
            Exception: Propagates exceptions raised during YAML file loading.
        """
        try:
            self._template_from_yaml = read_yaml(RESEARCH_PROMPTS_PATH)
            logger.info("Successfully loaded research prompt configuration from %s", RESEARCH_PROMPTS_PATH)
        except Exception as e:
            logger.error("Failed to load research prompt configuration from %s: %s", RESEARCH_PROMPTS_PATH, e)
            raise

        source_selection_prompt_template = PromptTemplate(
            template=self.get_template('source_selection_prompt_template'),
            input_variables=['query', 'source_list'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=SourceSelectionResponse
                ).get_format_instructions()
            }
        )

        self.source_selection_prompt = Prompt(
            adapter=PromptTemplateAdapter(source_selection_prompt_template)
        )

        relevance_check_prompt_template = PromptTemplate(
            template=self.get_template('relevance_check_prompt_template'),
            input_variables=['query', 'response'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=RelevanceEvaluationResponse
                ).get_format_instructions()
            }
        )

        self.relevance_check_prompt = Prompt(
            adapter=PromptTemplateAdapter(relevance_check_prompt_template)
        )

        generate_response_prompt_template = PromptTemplate(
            template=self.get_template('generate_response_prompt_template'),
            input_variables=['query', 'results'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=GeneratedResponse
                ).get_format_instructions()
            }
        )
        self.generate_response_prompt = Prompt(
            adapter=PromptTemplateAdapter(generate_response_prompt_template)
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
