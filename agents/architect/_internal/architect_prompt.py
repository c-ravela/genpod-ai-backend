from os import getcwd, path

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from core.prompt import *
from models.architect_models import ProjectDetails, TaskList, TaskResponse
from utils.logs.logging_utils import logger
from utils.yaml_utils import read_yaml

ARCHITECT_PROMPT_PATH = path.join(getcwd(), "prompts", "architect_prompts.yaml")

class ArchitectPrompts:
    """
    ArchitectPrompts contains templates for guiding the Architect agent in its tasks.

    It includes templates for initial project requirements generation and for providing
    additional information during project implementation. These templates ensure that
    the Architect agent can effectively assist users in implementing their projects,
    adhering to best practices in microservice architecture, project folder structure,
    and clean-code development.
    """

    def __init__(self, use_rag: bool):
        """
        Initializes the ArchitectPrompts instance by loading prompt templates from YAML and 
        constructing corresponding prompt objects.

        Args:
            use_rag (bool): A flag indicating whether RAG instructions should be applied
                            for those prompts that support RAG augmentation.
        """
        logger.info("Initializing ArchitectPrompts with use_rag=%s", use_rag)
        self.use_rag = use_rag
        
        try:
            self._template_from_yaml = read_yaml(ARCHITECT_PROMPT_PATH)
        except Exception as e:
            logger.error("Failed to load architect prompt configuration from %s: %s", ARCHITECT_PROMPT_PATH, e)
            raise

        project_summary_prompt_template = PromptTemplate(
            template=self.get_template('project_summary_prompt_template'),
            input_variables=['user_request', 'task_description'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=TaskResponse
                ).get_format_instructions()
            }
        )
        logger.debug("Created project summary prompt template.")
        self.project_summary_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(project_summary_prompt_template),
            use_rag=self.use_rag
        )
        logger.info("Initialized project_summary_prompt with use_rag=%s", self.use_rag)

        system_architecture_prompt_template = PromptTemplate(
            template=self.get_template('system_architecture_prompt_template'),
            input_variables=['project_overview'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=TaskResponse
                ).get_format_instructions()
            }
        )
        logger.debug("Created system architecture prompt template.")
        self.system_architecture_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(system_architecture_prompt_template),
            use_rag=self.use_rag
        )
        logger.info("Initialized system_architecture_prompt with use_rag=%s", self.use_rag)

        file_structure_prompt_template = PromptTemplate(
            template=self.get_template('file_structure_prompt_template'),
            input_variables=["project_overview", "system_architecture"],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=TaskResponse
                ).get_format_instructions()
            }
        )
        logger.debug("Created file structure prompt template.")
        self.file_structure_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(file_structure_prompt_template),
            use_rag=self.use_rag
        )
        logger.info("Initialized file_structure_prompt with use_rag=%s", self.use_rag)

        microservice_design_prompt_template = PromptTemplate(
            template=self.get_template('microservice_design_prompt_template'),
            input_variables=["project_overview", "system_architecture"],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=TaskResponse
                ).get_format_instructions()
            }
        )
        logger.debug("Created microservice design prompt template.")
        self.microservice_design_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(microservice_design_prompt_template),
            use_rag=self.use_rag
        )
        logger.info("Initialized microservice_design_prompt with use_rag=%s", self.use_rag)

        tasks_summary_prompt_template = PromptTemplate(
            template=self.get_template('tasks_summary_prompt_template'),
            input_variables=["project_overview", "system_architecture", "microservice_design"],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=TaskResponse
                ).get_format_instructions()
            }
        )
        logger.debug("Created tasks summary prompt template.")
        self.tasks_summary_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(tasks_summary_prompt_template),
            use_rag=self.use_rag
        )
        logger.info("Initialized tasks_summary_prompt with use_rag=%s", self.use_rag)

        code_standards_prompt_template = PromptTemplate(
            template=self.get_template('code_standards_prompt_template'),
            input_variables=["user_request", "user_requested_standards"],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=TaskResponse
                ).get_format_instructions()
            }
        )
        logger.debug("Created code standards prompt template.")
        self.code_standards_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(code_standards_prompt_template),
            use_rag=self.use_rag
        )
        logger.info("Initialized code_standards_prompt with use_rag=%s", self.use_rag)

        implementation_details_prompt_template = PromptTemplate(
            template=self.get_template('implementation_details_prompt_template'),
            input_variables=[
                "system_architecture",
                "microservice_design",
                "file_structure",
            ],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=TaskResponse
                ).get_format_instructions()
            }
        )
        logger.debug("Created implementation details prompt template.")
        self.implementation_details_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(implementation_details_prompt_template),
            use_rag=self.use_rag
        )
        logger.info("Initialized implementation_details_prompt with use_rag=%s", self.use_rag)

        license_details_prompt_template = PromptTemplate(
            template=self.get_template('license_details_prompt_template'),
            input_variables=["user_request", "license_text"],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=TaskResponse
                ).get_format_instructions()
            }
        )
        logger.debug("Created license details prompt template.")
        self.license_details_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(license_details_prompt_template),
            use_rag=self.use_rag
        )
        logger.info("Initialized license_details_prompt with use_rag=%s", self.use_rag)

        tasks_extraction_prompt_template = PromptTemplate(
            template=self.get_template('tasks_extraction_prompt_template'),
            input_variables=['tasks_summary'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=TaskList
                ).get_format_instructions()
            }
        )
        logger.debug("Created tasks extraction prompt template.")
        self.tasks_extraction_prompt = Prompt(
            adapter=PromptTemplateAdapter(tasks_extraction_prompt_template)
        )
        logger.info("Initialized tasks_extraction_prompt without RAG wrapping.")

        gather_project_details_prompt_template = PromptTemplate(
            template=self.get_template('gather_project_details_prompt_template'),
            input_variables=['user_request'],
            partial_variables={
                "format_instructions": PydanticOutputParser(
                    pydantic_object=ProjectDetails
                ).get_format_instructions()
            }
        )
        logger.debug("Created gather project details prompt template.")
        self.gather_project_details_prompt = Prompt(
            adapter=PromptTemplateAdapter(gather_project_details_prompt_template)
        )
        logger.info("Initialized gather_project_details_prompt without RAG wrapping.")

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
