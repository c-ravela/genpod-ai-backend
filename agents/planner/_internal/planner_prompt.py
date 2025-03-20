from os import getcwd, path

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from core.prompt import Prompt, PromptTemplateAdapter, RagInstructionsPrompt
from models.planner_models import Segregation
from utils.logger import logger
from utils.yaml_utils import read_yaml

PLANNER_PROMPTS_PATH = path.join(getcwd(), "prompts", "planner_prompts.yaml")


class PlannerPrompts:
    """
    A class to manage and provide various planner prompt templates, with optional Retrieval-Augmented Generation (RAG)
    instructions. The prompt templates are loaded from a YAML configuration file.

    Attributes:
        use_rag (bool): Flag indicating whether to use RAG instructions with prompts.
        task_breakdown_prompt (RagInstructionsPrompt): Prompt for task breakdown instructions.
        detailed_requirements_prompt (RagInstructionsPrompt): Prompt for detailed requirements.
        segregation_prompt (RagInstructionsPrompt): Prompt for segregation instructions.
        issues_segregation_prompt (RagInstructionsPrompt): Prompt for segregation of issues.
    """

    def __init__(self, use_rag: bool):
        """
        Initializes the PlannerPrompts instance by loading the YAML configuration and setting up various prompt templates.

        Args:
            use_rag (bool): A flag indicating whether the prompts should include RAG instructions.
        
        Raises:
            Exception: Propagates any exception raised during YAML configuration file loading.
        """
        logger.info("Initializing PlannerPrompts with use_rag=%s", use_rag)
        self.use_rag = use_rag

        try:
            self._template_from_yaml = read_yaml(PLANNER_PROMPTS_PATH)
            logger.debug("Successfully loaded YAML configuration from %s", PLANNER_PROMPTS_PATH)
        except Exception as e:
            logger.error("Failed to load architect prompt configuration from %s: %s", PLANNER_PROMPTS_PATH, e)
            raise

        task_breakdown_prompt_template = PromptTemplate(
            template=self.get_template('task_breakdown_prompt_template'),
            input_variables=["deliverable", "context", "feedback"]
        )

        self.task_breakdown_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(task_breakdown_prompt_template),
            use_rag=self.use_rag
        )

        detailed_requirements_prompt_template = PromptTemplate(
            template=self.get_template('detailed_requirements_prompt_template'),
            input_variables=["backlog", "deliverable", "context", "feedback"]
        )

        self.detailed_requirements_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(detailed_requirements_prompt_template),
            use_rag=self.use_rag
        )

        segregation_prompt_template = PromptTemplate(
            template=self.get_template('segregation_prompt_template'),
            input_variables=['work_package'],
            partial_variables= {
                "format_instructions": PydanticOutputParser(pydantic_object=Segregation).get_format_instructions()
            }
        )

        self.segregation_prompt = Prompt(
            adapter=PromptTemplateAdapter(segregation_prompt_template)
        )

        issues_segregation_prompt_template = PromptTemplate(
            template=self.get_template('issues_segregation_prompt_template'),
            input_variables=['file_content', 'issue_details'],
            partial_variables={
                "format_instruction": PydanticOutputParser(pydantic_object=Segregation).get_format_instructions()
            }
        )

        self.issues_segregation_prompt = Prompt(
            adapter=PromptTemplateAdapter(issues_segregation_prompt_template)
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
