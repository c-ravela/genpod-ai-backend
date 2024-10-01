from typing import List

from pydantic import BaseModel, Field, field_validator, StrictBool, field_validator


class BacklogList(BaseModel):
    backlogs: List[str] = Field(..., description="List of backlog items")

    @field_validator('backlogs')
    @classmethod
    def check_backlog_items(cls, v):
        if not isinstance(v, list):
            raise ValueError('Backlogs must be a list')
        for item in v:
            if not isinstance(item, str):
                raise ValueError('Each backlog item must be a string')
        return v

class Segregation(BaseModel):
    """
    A model to classify tasks based on whether they require function creation or updation
    and provide a reason for classification.
    """
    
    requires_function_creation: StrictBool = Field(
        description="""
        This field holds the boolean value that specifies "True" if the task requires function creation,
        or "False" if the task does not require function creation.
        """,
        required=True
    )

    classification_reason: str = Field(
        description="This field contains the reason for the task classification.",
        default=""
    )

    @field_validator('requires_function_creation', mode="before")
    def validate_requires_function_creation(cls, value) -> StrictBool:
        if value is None:
            raise ValueError("The 'requires_function_creation' field is required and must not be null.")
        return value
