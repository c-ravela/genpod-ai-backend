from os import getcwd, path
from typing import Any, Dict

from pydantic import Field

from core.prompt.base_prompt import BasePrompt
from core.prompt.prompt_template_adapters.base_prompt_template_adapter import *
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
            - 'template': A multi-line string that represents the RAG instruction text.
            - 'position': A string indicating where the instruction should be applied,
                          either "top" or "bottom". If no position is provided, "top" is assumed.

        Returns:
            dict: A dictionary with keys "top" and "bottom" containing the aggregated RAG instructions.
        """
        logger.info("Loading RAG instructions from %s", filepath)
        try:
            instructions = load_instructions_from_yaml(filepath)
            logger.debug("RAG instructions loaded: %s", instructions)
            return instructions
        except Exception as e:
            logger.error("Failed to load RAG instructions from %s: %s", filepath, e)
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
        super().__init__(adapter=adapter, use_rag=use_rag)
        if not self.rag_instructions:
            self.rag_instructions = self.load_rag_instructions()
        logger.debug("RagInstructionsPrompt initialized with rag_instructions: %s and use_rag: %s", 
                     self.rag_instructions, self.use_rag)

    def _format_prompt(self, **kwargs: Any) -> str:
        """
        Generates the core prompt text, optionally wrapping it with RAG-specific instructions.

        If use_rag is True, the output will be:
            <RAG Top Instructions>
            <Actual Prompt Content (formatted by the adapter)>
            <RAG Bottom Instructions>
        Otherwise, it simply returns the adapter's formatted prompt.

        Args:
            **kwargs: Keyword arguments for prompt formatting.

        Returns:
            str: The core prompt text.
        """
        logger.info("Formatting prompt in RagInstructionsPrompt with kwargs: %s", kwargs)
        
        base_text = self.adapter.format(**kwargs)
        logger.debug("Base prompt text from adapter: %s", base_text)
       
        if not self.use_rag:
            logger.info("use_rag is False; returning prompt text without RAG instructions.")
            return base_text

        rag_top = self.rag_instructions.get("top", "")
        rag_bottom = self.rag_instructions.get("bottom", "")

        formatted_text = f"{rag_top}\n{base_text}\n{rag_bottom}".strip()
        logger.debug("Core prompt text after adding RAG instructions: %s", formatted_text)
        return formatted_text
