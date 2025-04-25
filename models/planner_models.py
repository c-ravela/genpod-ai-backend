from typing import List

from pydantic import (BaseModel, Field, RootModel, StrictBool, field_validator,
                      model_validator)


class BacklogList(RootModel[List[str]]):
    @field_validator('root', mode="before")
    @classmethod
    def check_backlogs(cls, v):
        if not isinstance(v, list):
            raise ValueError("Input must be a list")
        for item in v:
            if not isinstance(item, str):
                raise ValueError("All backlog items must be strings")
        return v

    def __iter__(self):
        return iter(self.root)


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
