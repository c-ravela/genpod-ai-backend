from os import getcwd, path
from typing import Any, Dict

from pydantic import Field

from core.prompt.base_prompt import BasePrompt
from core.prompt.prompt_template_adapters.base_prompt_template_adapter import \
    BasePromptTemplateAdapter
from core.prompt.utils import load_instructions_from_yaml
from utils.logs.logging_utils import logger

GLOBAL_RAG_INSTRUCTIONS_PATH = path.join(getcwd() , "prompts", "rag_retrieval_instructions.yaml")


class RagInstructionsPrompt(BasePrompt):
    """
    RagInstructionsPrompt augments a BasePrompt by inserting RAG-specific instructions
    between the actual prompt content and the common instructions.

    When use_rag is True, the final prompt is composed as follows:
    
        <Common Top Instructions>
        <RAG Top Instructions>
        <Actual Prompt Content (formatted by the adapter)>
        <RAG Bottom Instructions>
        <Common Bottom Instructions>
    
    If use_rag is False, the prompt renders using BasePrompt's behavior (i.e., without RAG instructions).

    Attributes:
        rag_instructions (dict): Aggregated RAG instructions with keys "top" and "bottom".
        use_rag (bool): Flag indicating whether RAG instructions should be applied.
    """
    rag_instructions: Dict[str, str] = Field(default_factory=dict, init=False)
    use_rag: bool

    @classmethod
    def load_rag_instructions(cls, filepath: str = GLOBAL_RAG_INSTRUCTIONS_PATH) -> Dict[str, str]:
        """
        Loads and aggregates RAG instructions from a YAML configuration file.
        Delegates the file reading and aggregation to load_instructions_from_yaml().

        The YAML file is expected to contain an "instructions" key whose value is an array
        of objects. Each object should have:
            - 'template': A multi-line string representing the RAG instruction text.
            - 'position': A string indicating where the instruction should be applied,
                          either "top" or "bottom". If no position is provided, "top" is assumed.

        Returns:
            Dict[str, str]: A dictionary with keys "top" and "bottom" containing the aggregated RAG instructions.

        Raises:
            Exception: If loading instructions fails.
        """
        logger.info("Loading RAG instructions from %s", filepath)
        try:
            instructions = load_instructions_from_yaml(filepath)
            logger.debug("RAG instructions loaded successfully: %s", instructions)
            return instructions
        except Exception as e:
            logger.error("Failed to load RAG instructions from %s: %s", filepath, e, exc_info=True)
            raise

    def __init__(self, *, adapter: BasePromptTemplateAdapter, use_rag: bool):
        """
        Initializes the RagInstructionsPrompt instance with a prompt template adapter and a RAG flag.

        Args:
            adapter (BasePromptTemplateAdapter): The adapter used for formatting the prompt template.
            use_rag (bool): Flag indicating whether RAG instructions should be applied.

        Raises:
            Exception: Propagates exceptions from loading RAG instructions.
        """
        logger.debug("Initializing RagInstructionsPrompt with use_rag=%s", use_rag)
        super().__init__(adapter=adapter, use_rag=use_rag)
        if not self.rag_instructions:
            self.rag_instructions = self.load_rag_instructions()
            logger.debug("RAG instructions set to: %s", self.rag_instructions)
        logger.info("RagInstructionsPrompt initialized with use_rag=%s", self.use_rag)

    def _format_prompt(self, **kwargs: Any) -> str:
        """
        Generates the core prompt text, optionally wrapping it with RAG-specific instructions.

        The method first generates the base prompt using the adapter. If use_rag is True,
        it then formats the RAG instructions (both top and bottom) using the same kwargs,
        and inserts them around the base prompt.

        Args:
            **kwargs: Keyword arguments for prompt formatting.

        Returns:
            str: The complete prompt text including RAG instructions if enabled.
        """
        logger.info("Starting prompt formatting in RagInstructionsPrompt with kwargs: %s", kwargs)
        base_text = self.adapter.format(**kwargs)
        logger.debug("Base prompt text from adapter: '%s'", base_text)
       
        if not self.use_rag:
            logger.info("use_rag is False; returning base prompt without RAG instructions.")
            return base_text

        rag_top_template = self.rag_instructions.get("top", "")
        logger.debug("RAG top template: '%s'", rag_top_template)
        rag_bottom_template = self.rag_instructions.get("bottom", "")
        logger.debug("RAG bottom template: '%s'", rag_bottom_template)

        try:
            rag_top = self.safe_format(rag_top_template, **kwargs)
            logger.debug("Formatted RAG top: '%s'", rag_top)
            rag_bottom = self.safe_format(rag_bottom_template, **kwargs)
            logger.debug("Formatted RAG bottom: '%s'", rag_bottom)
        except ValueError as e:
            logger.error("Error formatting RAG instructions: %s", e, exc_info=True)
            raise

        formatted_text = f"{rag_top}\n{base_text}\n{rag_bottom}".strip()
        logger.info("Final prompt text after applying RAG instructions: '%s'", formatted_text)
        return formatted_text
