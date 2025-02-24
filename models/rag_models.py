from pydantic import BaseModel, Field, field_validator


class BinaryScore(BaseModel):
    score: bool = Field(
        description="A binary response indicating either True (yes) or False (no)."
    )
    
    @field_validator("score", mode="before")
    def normalize_score(cls, v):
        if isinstance(v, str):
            v = v.lower().strip()
            if v == "yes":
                return True
            elif v == "no":
                return False
            else:
                raise ValueError("score string must be either 'yes' or 'no'")
        if isinstance(v, bool):
            return v
        raise ValueError("score must be a boolean or a string 'yes'/'no'")


class PromptResponse(BaseModel):
    """
    A generic base model for LLM prompt outputs.

    Attributes:
        response (str): The answer produced by the LLM. If the model cannot provide a definitive answer,
            it should output "I don't know".
        is_unknown (bool): A flag that indicates whether the response represents a lack of an answer. 
            Set to True if the response is "I don't know", otherwise False.
        metadata (Dict[str, Any]): Optional metadata associated with the response.
    """
    response: str = Field(
        description="The answer produced by the LLM. If no answer is available, this should be 'I don't know'."
    )
    is_unknown: bool = Field(
        description="A flag indicating if the response is 'I don't know' (True) or if a valid answer is provided (False)."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "response": "I don't know",
                "is_unknown": True,
            }
        }
