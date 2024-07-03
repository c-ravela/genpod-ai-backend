"""
This module defines the data model for the output of the Coder agent. 

The Coder agent is responsible for completing tasks in a project. The output of 
the Coder agent includes information about the steps to complete a task, 
the files to be created, the location of the code, the actual code.
"""

from typing_extensions import ClassVar

from pydantic import Field
from pydantic import BaseModel

class ToolCall(BaseModel):
    """
    """
    name: str = Field(
        description="The name of the tool to use", 
        required=True
    )

    args: dict[str, str] = Field(
        description="arguments to the tools",
        required=True
    )

class CoderModel(BaseModel):
    """
    A data model representing the output of the Coder agent.

    This model includes various fields that capture the details of the task 
    completion process, such as the steps to complete the task, the files to
    be created, the location of the code, and the actual code.
    """
    can_complete_task: bool = Field(
        description="can task be completed?",
        required=True
    )

    task_abandon_remarks: str = Field(
        description="reason why task was abandoned.",
        required=True
    )

    is_add_info_needed: bool = Field(
        description="If you need additional ifnormation to complete a task or not.",
        required=True
    )

    question_for_additional_info: str = Field(
        description="what new information you need?"
    )

    files_to_create: str = Field(
        description="A list of absolute file paths that need to be created as part of the task", 
        required=True
    )

    code: str = Field(
        description="The complete, well-documented working code that adheres to all "
        "standards requested with the programming language, framework user requested ", 
        required=True
    )
    
    infile_license_comments: dict[str, str] = Field(
        description="The multiline standard license comment which goes on top of each file."
        "key should be the extension of the file, ex: language: python, key: .py"
        "language: C++, key: .cpp, language: Markdown, key: .md, language: C#, key: .cs"
        "value of these any of these keys should be the license commented in multiline "
        "format.",
        required=True
    )

    tool_calls: list[ToolCall] = Field(
        description="List of tool calls that need to be made to complete the task",
        required=True
    )

    description: ClassVar[str] = "Schema representing the output from the "
    "Coder agent upon task completion."
