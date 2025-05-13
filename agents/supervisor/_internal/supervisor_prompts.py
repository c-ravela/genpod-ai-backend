from os import getcwd, path

from langchain_core.prompts import PromptTemplate

from core.prompt import Prompt, PromptTemplateAdapter
from utils.logger import logger
from utils.yaml_utils import read_yaml

SUPERVISOR_PROMPTS_PATH = path.join(getcwd(), "prompts", "supervisor_prompts.yaml")


class SupervisorPrompts:
    def __init__(self, use_rag: bool):
        self.use_rag = use_rag

        try:
            self._template_from_yaml = read_yaml(SUPERVISOR_PROMPTS_PATH)
        except Exception as e:
            logger.error("Failed to load supervisor prompt configuration from %s: %s", SUPERVISOR_PROMPTS_PATH, e)
            raise

        delegator_prompt_template = PromptTemplate(
            template=self.get_template('delegator_prompt_template'),
            input_variables=["question", "document"]
        )
        self.delegator_prompt = Prompt(
            adapter=PromptTemplateAdapter(delegator_prompt_template)
        )

        response_evaluator_prompt_template = PromptTemplate(
            template=self.get_template('response_evaluator_prompt_template'),
            input_variables=["team_members", "response", "user_query"],
        )
        self.response_evaluator_prompt = Prompt(
            adapter=PromptTemplateAdapter(response_evaluator_prompt_template)
        )

        architect_call_prompt_template = PromptTemplate(
            template=self.get_template('architect_call_prompt_template')
        )
        self.architect_call_prompt = Prompt(
            adapter=PromptTemplateAdapter(architect_call_prompt_template)
        )

        additional_info_req_prompt_template = PromptTemplate(
            template=self.get_template('additional_info_req_prompt_template')
        )
        self.additional_info_req_prompt = Prompt(
            adapter=PromptTemplateAdapter(additional_info_req_prompt_template)
        )

        init_rag_questionaire_prompt_template = PromptTemplate(
            template=self.get_template('init_rag_questionaire_prompt_template'),
            input_variables=["user_prompt", "context"]
        )
        self.init_rag_questionaire_prompt = Prompt(
            adapter=PromptTemplateAdapter(init_rag_questionaire_prompt_template)
        )

        follow_up_questions_template = PromptTemplate(
            template=self.get_template('follow_up_questions_template'),
            input_variables=["user_query", "initial_rag_response"]
        )
        self.follow_up_questions = Prompt(
            adapter=PromptTemplateAdapter(follow_up_questions_template)
        )

        ideal_init_rag_questionaire_prompt_template = PromptTemplate(
            template=self.get_template('ideal_init_rag_questionaire_prompt_template'),
            input_variables=["user_prompt", "context"]
        )
        self.ideal_init_rag_questionaire_prompt = Prompt(
            adapter=PromptTemplateAdapter(ideal_init_rag_questionaire_prompt_template)
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
