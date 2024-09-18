from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

class FileIssue(BaseModel):
    """
    Represents an issue found in a file. This model is used to detail problems or errors discovered during analysis.
    """

    file_path: str = Field(
        description="The path to the file where the issue was found.",
        default="",
        title="File Path",
        examples=["/path/to/file.py"]
    )

    line_number: Optional[int] = Field(
        default=None,
        description="The line number in the file where the issue occurs.",
        title="Line Number",
        examples=[42]
    )

    description: str = Field(
        description="A detailed description of the issue.",
        default="",
        title="Issue Description",
        examples=["Undefined variable 'x' in function 'foo'."]
    )

    suggestions: Optional[List[str]] = Field(
        default=None,
        description="Suggestions for resolving the issue.",
        title="Suggestions",
        examples=[ "Define the variable 'x' before use", "Check variable scope and initialization" ]
    )

    @model_validator(mode="before")
    def check__required_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        file_path = values.get('file_path')
        description = values.get('description')

        if not file_path or not description:
            raise ValueError('Both file_path and description must be provided')

        return values

class ReviewerOutput(BaseModel):
    """
    Represents the output of a review process, which includes a list of issues found in files.
    """

    file_issues: List[FileIssue] = Field(
        default_factory=list,
        description="A list of issues identified in files during the review process.",
        title="File Issues",
        examples=[
            [
                {
                    "file_path": "/path/to/file1.py",
                    "line_number": 10,
                    "description": "Syntax error in file1.py",
                    "suggestions": [
                        "Check for missing colons",
                        "Review function definitions"
                    ]
                },
                {
                    "file_path": "/path/to/file2.py",
                    "line_number": 20,
                    "description": "Deprecated function used in file2.py",
                    "suggestions": [
                        "Replace with the latest function",
                        "Refer to the updated API documentation"
                    ]
                }
            ]
        ]
    )

    @model_validator(mode="before")
    def check__reviewer_output(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        file_issues = values.get('file_issues')

        if file_issues is None:
            raise ValueError('file_issues cannot be None. Provide an empty list if there are no issues.')
        
        if not isinstance(file_issues, list):
            raise ValueError('file_issues must be a list')
        
        for item in file_issues:
            if not isinstance(item, dict):
                raise ValueError('Each item in file_issues must be a dictionary.')
             
            try:
                FileIssue(**item)
            except ValueError as e:
                raise ValueError(f'Invalid item in file_issues: {e}')

        return values
