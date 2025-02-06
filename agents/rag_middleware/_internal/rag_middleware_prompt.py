from os import getcwd, path

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from core.prompt import *
from models import RagSelectionResponse
from utils.logs.logging_utils import logger
from utils.yaml_utils import read_yaml

RAG_MIDDLEWARE_PROMPTS_PATH = path.join(getcwd(), "prompts", "rag_middleware_prompts.yaml")


class RAGMiddlewarePrompts:

    def __init__(self):

        try:
            self._template_from_yaml = read_yaml(RAG_MIDDLEWARE_PROMPTS_PATH)
        except Exception as e:
            logger.error("Failed to load architect prompt configuration from %s: %s", RAG_MIDDLEWARE_PROMPTS_PATH, e)
            raise
        
        rag_agent_selection_prompt_template = PromptTemplate(
            template=self.get_template('rag_agent_selection_prompt_template'),
            input_variables=['agent_list', 'query'],
            partial_variables={
                'format_instructions': PydanticOutputParser(
                    pydantic_object=RagSelectionResponse
                ).get_format_instructions()
            }
        )
        self.rag_agent_selection_prompt = Prompt(
            adapter=PromptTemplateAdapter(rag_agent_selection_prompt_template)
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
