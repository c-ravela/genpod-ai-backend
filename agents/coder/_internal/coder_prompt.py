from os import getcwd, path

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from core.prompt import PromptTemplateAdapter, RagInstructionsPrompt
from models.coder_models import CodeGenerationPlan
from utils.logs.logging_utils import logger
from utils.yaml_utils import read_yaml

CODER_PROMPTS_PATH = path.join(getcwd(), "prompts", "coder_prompts.yaml")


class CoderPrompts:

    def __init__(self, use_rag: bool):
        self.use_rag = use_rag

        try:
            self._template_from_yaml = read_yaml(CODER_PROMPTS_PATH)
        except Exception as e:
            logger.error("Failed to load coder prompt configuration from %s: %s", CODER_PROMPTS_PATH, e)
            raise

        code_generation_prompt_template = PromptTemplate(
            template=self.get_template('code_generation_prompt_template'),
            input_variables=[
                'project_name',
                'project_path',
                'error_message',
                'issue',
                'file_path',
                'file_content',
                'function_signatures',
                'unit_test_code'
            ],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=CodeGenerationPlan
                ).get_format_instructions()
            }
        )
        self.code_generation_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(code_generation_prompt_template),
            use_rag=self.use_rag
        )

        issue_resolution_prompt_template = PromptTemplate(
            template=self.get_template('issue_resolution_prompt_template'),
            input_variables=[
                'project_name',
                'project_path',
                'error_message',
                'issue',
                'file_path',
                'file_content',
                'function_signatures',
                'unit_test_code'
            ],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=CodeGenerationPlan
                ).get_format_instructions()
            }
        )
        self.issue_resolution_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(issue_resolution_prompt_template),
            use_rag=self.use_rag
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
