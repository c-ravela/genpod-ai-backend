from pydantic import BaseModel, Field, field_validator

from langchain.prompts import PromptTemplate
from utils.logs.logging_utils import logger


class PromptWithConfig(BaseModel):
    """
    Wraps a PromptTemplate instance with optional Retrieval-Augmented Generation (RAG) configuration.
    
    Attributes:
        template (PromptTemplate): The prompt instance adhering to PromptTemplate interface.
        enable_rag_retrival (bool): If True, prepend RAG instructions when rendering the prompt.
    """
    template: PromptTemplate
    enable_rag_retrival: bool = Field(
        default=False,
        description="If True, prepend RAG instructions when rendering the prompt."
    )


    class Config:
        # Allows storing arbitrary Python objects like 'PromptTemplateAdapter'
        arbitrary_types_allowed = True

    @field_validator("template")
    @classmethod
    def validate_template(cls, v):
        """
        Ensure 'template' is an instance of PromptTemplate or its subclasses.
        """
        if not isinstance(v, PromptTemplate):
            logger.error(f"Invalid template type: {type(v)}. Expected PromptTemplate.")
            raise ValueError(
                "template must be an instance of PromptTemplate or its subclasses."
            )
        logger.debug(f"Prompt template of type {type(v)} validated successfully.")
        return v
