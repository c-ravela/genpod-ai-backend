from os import getcwd, path

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from core.prompt import Prompt, PromptTemplateAdapter, RagInstructionsPrompt
from models.tests_generator_models import (FileFunctionSignatures,
                                           TestCodeGeneration)
from utils.logs.logging_utils import logger
from utils.yaml_utils import read_yaml

TESTS_GENERATOR_PROMPTS_PATH = path.join(getcwd(), "prompts", "architect_prompts.yaml")


class TestsGeneratorPrompts:
    """
    Initializes prompt templates for generating test code and function skeletons.

    The class reads a YAML configuration file to retrieve multi-line prompt templates,
    constructs corresponding LangChain prompt objects with appropriate input and partial
    variables, and provides them for use in test generation workflows.

    Attributes:
        use_rag (bool): Flag to determine if retrieval-augmented generation should be used.
        test_generation_prompt (RagInstructionsPrompt): Prompt for generating tests.
        skeleton_generation_prompt (RagInstructionsPrompt): Prompt for generating function skeletons.
        skeleton_generation_for_issue_prompt (RagInstructionsPrompt): Prompt for generating skeletons for a specific issue.
        unit_test_generation_for_issue_prompt (RagInstructionsPrompt): Prompt for generating unit tests for a specific issue.
    """
    def __init__(self, use_rag: bool):
        """
        Initializes the TestsGeneratorPrompts instance by loading the YAML configuration
        and setting up various prompt templates.

        Args:
            use_rag (bool): Whether to enable retrieval-augmented generation (RAG) for prompts.

        Raises:
            Exception: Propagates any exception that occurs while reading the YAML configuration.
        """
        self.use_rag = use_rag
        logger.info("Initializing TestsGeneratorPrompts with use_rag=%s", use_rag)

        try:
            self._template_from_yaml = read_yaml(TESTS_GENERATOR_PROMPTS_PATH)
            logger.debug("Successfully loaded YAML configuration from '%s'.", TESTS_GENERATOR_PROMPTS_PATH)
        except Exception as e:
            logger.error("Failed to load tests generator prompt configuration from %s: %s",
                         TESTS_GENERATOR_PROMPTS_PATH, e)
            raise


        test_generation_prompt_template = PromptTemplate(
            template=self.get_template('test_generation_prompt_template'),
            input_variables=['project_name', 'project_path', 'requirements_document', 'error_message', 'task' , 'functions_skeleton'],
            partial_variables= {
                "format_instructions": PydanticOutputParser(pydantic_object=TestCodeGeneration).get_format_instructions()
            }
        )
        self.test_generation_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(test_generation_prompt_template),
            use_rag=self.use_rag
        )

        skeleton_generation_prompt_template = PromptTemplate(
            template=self.get_template('skeleton_generation_prompt_template'),
            input_variables=['project_name', 'project_path', 'requirements_document', 'error_message', 'task' ],
            partial_variables= {
                "format_instructions": PydanticOutputParser(pydantic_object=FileFunctionSignatures).get_format_instructions()
            }
        )
        self.skeleton_generation_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(skeleton_generation_prompt_template),
            use_rag=self.use_rag
        )

        skeleton_generation_for_issue_prompt_template = PromptTemplate(
            template=self.get_template('skeleton_generation_for_issue_prompt_template'),
            input_variables=['file_content', 'issue_details', 'project_name', 'project_path', 'requirements_document', 'error_message', 'format_instructions'],
            partial_variables={
                "format_instructions": PydanticOutputParser(pydantic_object=FileFunctionSignatures).get_format_instructions()
            }
        )
        self.skeleton_generation_for_issue_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(skeleton_generation_for_issue_prompt_template),
            use_rag=self.use_rag
        )

        unit_test_generation_for_issue_prompt_template = PromptTemplate(
            template=self.get_template('unit_test_generation_for_issue_prompt_template'),
            input_variables=['project_name', 'project_path', 'file_content', 'issue_details', 'requirements_document', 'error_message', 'functions_skeleton'],
            partial_variables={
                "format_instructions": PydanticOutputParser(pydantic_object=TestCodeGeneration).get_format_instructions()
            }
        )
        self.unit_test_generation_for_issue_prompt = RagInstructionsPrompt(
            adapter=PromptTemplateAdapter(unit_test_generation_for_issue_prompt_template),
            use_rag=self.use_rag
        )

        logger.info("TestsGeneratorPrompts initialization complete.")

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
