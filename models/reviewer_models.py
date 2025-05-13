from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class FileIssue(BaseModel):
    """
    Represents an issue found in a file. This model is used to detail problems or 
    errors discovered during analysis.
    """

    file_path: str = Field(
        description="The path to the file where the issue was found.",
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
        title="Issue Description",
        examples=["Undefined variable 'x' in function 'foo'."]
    )

    suggestions: Optional[List[str]] = Field(
        default=None,
        description="Suggestions for resolving the issue.",
        title="Suggestions",
        examples=[
            "Define the variable 'x' before use", 
            "Check variable scope and initialization"
        ]
    )

    @model_validator(mode="before")
    def check__required_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        file_path = values.get('file_path')
        description = values.get('description')

        if not file_path or not description:
            raise ValueError('Both file_path and description must be provided')

        return values


class IssuesReport(BaseModel):
    """
    Represents the output of a review process, which includes a list of issues found in
    files.
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
            raise ValueError(
                'file_issues cannot be None. Provide an empty list if there are no issues.'
            )

        if not isinstance(file_issues, list):
            raise ValueError('file_issues must be a list')
       
        for item in file_issues:
            if not isinstance(item, dict):
                raise ValueError('Each item in file_issues must be a dictionary.')

            if not isinstance(item, FileIssue):
                try:
                    FileIssue(**item)
                except ValueError as e:
                    raise ValueError(f'Invalid item in file_issues: {e}')

        return values


class DockerfileSelectionResponse(BaseModel):
    """
    Represents the response for the Dockerfile selection prompt.
    
    Attributes:
        id (str): The id of the selected Dockerfile object.
    """
    id: str = Field(
        ...,
        description="The id of the selected Dockerfile object."
    )


class DockerSandboxExecutorParams(BaseModel):
    """
    Represents the parameters required to execute code in a Docker sandbox.
    
    Attributes:
        language (str): The programming language to use for sandbox execution.
        command (str): The command to execute inside the container.
        libraries (Optional[List[str]]): Optional list of libraries to install prior to execution.
    """
    language: str = Field(
        ...,
        description="The programming language to use for sandbox execution."
    )
    command: str = Field(
        ...,
        description="The command to execute inside the container."
    )
    libraries: Optional[List[str]] = Field(
        None,
        description="Optional list of libraries to install prior to execution."
    )

class LanguageSelectionResponse(BaseModel):
    """
    Represents the selected programming language for the project.

    Attributes:
        language (str): The programming language selected based on the provided requirements.
    """
    language: str = Field(
        ...,
        description="The programming language selected for the project based on the provided requirements."
    )


class FilePathSelectionResponse(BaseModel):
    """
    Represents the selected file or directory path for executing a check (e.g., lint or test).
    
    Attributes:
        file_path (str): The file or directory path chosen for the check.
    """
    file_path: str = Field(
        ...,
        description="The file or directory path selected for executing the check."
    )
