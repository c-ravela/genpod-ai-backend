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
        description="A list of absolute file paths that need to be created as part of the current task", 
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

class CodeGeneration(BaseModel):
    """
    """

    files_to_create: list[str] = Field(
        description="""
        A list of absolute file paths that need to be created as part of the current task
        "
        [
            'absolute_file_path1', 
            'absolute_file_path2', 
            'absolute_file_path3',
            .
            .
            .
            .,
            'absolute_file_pathN'
        ]        
        """, 
        required=True
    )

    code: dict[str, str] = Field(
        description="""
        A dictionary where each key-value pair represents a file and its corresponding code. The key 
        should be the absolute path to the file, and the value should be the well-documented working 
        code for that particular file. The code should adhere to all the requirements and standards 
        provided.
        """, 
        required=True
    )

    infile_license_comments: dict[str, str] = Field(
        description="""
        The standard license text multiline comment which goes on top of each file, key of the dict 
        should be the extension of the file. 
        "
            {
                ".py": "multiline commment",
                ".md": "multiline comment",
                ".yml": "multiline comment",
            }
        "
        """,
        required=True
    )

    commands_to_execute: dict[str, str] = Field(
        description="""
        This field represents a dictionary of commands intended to be executed on a Linux terminal. Each key-value pair in the dictionary corresponds to an absolute path (the key) and a specific command (the value) to be executed at that path.

        Please adhere to the following guidelines while populating this field:
        - The key should be the absolute path where the command is to be run.
        - Only commands from the approved list are allowed. The approved commands include 'mkdir', 'docker', 'python', 'python3', 'pip', 'virtualenv', 'mv', 'pytest', and 'touch', 'git'.
        - For security reasons, the use of certain symbols is restricted. Specifically, the following symbols are not permitted: '&&', '||', '|', ';'.

        Please ensure that the commands and their parameters are correctly formatted to prevent any execution errors.
        """,
        required=True
    )
