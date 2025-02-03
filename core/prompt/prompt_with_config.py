from langchain.prompts import PromptTemplate
from pydantic import BaseModel, ConfigDict, Field, field_validator

from utils.logs.logging_utils import logger


class PromptWithConfig(BaseModel):
    """
    Wraps a PromptTemplate instance with optional Retrieval-Augmented Generation (RAG) configuration.
    
    Attributes:
        template (PromptTemplate): The prompt instance adhering to PromptTemplate interface.
        enable_rag_retrival (bool): If True, prepend RAG instructions when rendering the prompt.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    template: PromptTemplate
    enable_rag_retrival: bool = Field(
        default=False,
        description="If True, prepend RAG instructions when rendering the prompt."
    )

    @field_validator("template")
    @classmethod
    def validate_template(cls, v):
        if not isinstance(v, PromptTemplate):
            logger.error(f"Invalid template type: {type(v)}. Expected PromptTemplate.")
            raise ValueError(
                "template must be an instance of PromptTemplate or its subclasses."
            )
        logger.debug(f"Prompt template of type {type(v)} validated successfully.")
        return v
