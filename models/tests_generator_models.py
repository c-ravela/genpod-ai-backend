"""
This module defines the data model for the output of the TestGenerator agent.

The TestGenerator agent is responsible for completing tasks in a project. The output of
the TestGenerator agent includes information about the steps to complete a task,
the files to be created, the location of the code, the actual code.
"""
import os
from typing import Dict, List

from pydantic import BaseModel, Field, field_validator


class FunctionSignature(BaseModel):
    """
    Represents the structure of a function, including its name, input parameters, 
    return type, and detailed description of its purpose.
    """
   
    function_name: str = Field(
        description="A concise and descriptive name for the function.",
        min_length=3,
        example="calculate_total"
    )
    
    input_params: List[str] = Field(
        description="A list of input parameters the function will take, including their types. Can be empty if no input is required.",
        default=[],
        example=["int price", "int quantity"]
    )
    
    return_type: List[str] = Field(
        description="The function's output, including its type and what it represents. Can be empty if there is no return value.",
        default=[],
        example=["int total"]
    )
    
    function_description: str = Field(
        description="A comprehensive description of the function's purpose and behavior.",
        min_length=10,
        example="This function calculates the total price by multiplying price by quantity."
    )

# TODO: The value should be a list of FunctionSignature objects to allow multiple functions per file.
# Returning a single function per file may not cover all possible edge cases or testing scenarios.
class FileFunctionSignatures(BaseModel):
    """
    Holds a mapping of file paths to their respective function signatures, represented by the FunctionSignature model.
    """
    function_signatures: Dict[str, FunctionSignature] = Field(
        description="A dictionary where each key is the absolute path to the file, and each value is a corresponding function signature."
    )

    @field_validator('function_signatures')
    def validate_function_signatures(cls, v: Dict[str, FunctionSignature]) -> Dict[str, FunctionSignature]:
        """
        Validator to ensure each value is a valid FunctionSignature instance and that keys are valid file paths.
        """
        for file_path, signature in v.items():
            # Validate that the key is a valid file path
            if not os.path.isabs(file_path):
                raise ValueError(f"'{file_path}' is not an absolute file path.")
            
            if not isinstance(signature, FunctionSignature):
                try:
                    v[file_path] = FunctionSignature(**signature)
                except Exception as e:
                    raise ValueError(f"Invalid FunctionSignature for file '{file_path}': {e}")
                
        return v

class TestCodeGeneration(BaseModel):
    """
    A list of absolute file paths that need to be created as part of the current task. 
    Each entry must be a valid, non-empty string representing a file path.
    """

    test_code: Dict[str, str] = Field(
        description="""
        A dictionary where each key-value pair represents a file and its corresponding code. 
        The key should be the absolute path to the file, and the value should be the well-documented working 
        unit test code for that particular file. Ensure that the value is non-empty and properly formatted.
        """,
        example={
            '/home/user/project/test/test_main.py': 'def test_main():\n    assert main() == 0'
        },
        required=True
    )

    infile_license_comments: Dict[str, str] = Field(
        description="""
        A dictionary mapping file extensions (e.g., '.py', '.md') to the standard license text 
        (multiline comments) for that file type. The key must be a valid file extension starting with a dot.
        """,
        default={},
        example={
            '.py': "''' \nSPDX-License-Identifier: Apache-2.0\nCopyright 2024\n'''"
        }
    )

    commands_to_execute: Dict[str, str] = Field(
        description="""
        A dictionary mapping absolute paths to commands that should be executed at those paths. 
        Only approved commands ('mkdir', 'docker', 'python', 'pytest', etc.) are allowed, and forbidden symbols 
        ('&&', '||', etc.) must not be used in the commands.
        """,
        default={},
        example={
            '/home/user/project/': 'mkdir new_directory',
            '/home/user/project/scripts/': 'python3 setup.py'
        }
    )

    @field_validator('commands_to_execute', mode="before")
    def validate_command(cls, v: Dict[str, str]):
        forbidden_symbols = ['&&', '||', '|', ';']
        allowed_commands = ['mkdir', 'docker', 'python', 'python3', 'pip', 'virtualenv', 'mv', 'pytest', 'touch', 'git']
        
        for path, command in v.items():
            # Ensure command does not contain forbidden symbols
            if any(symbol in command for symbol in forbidden_symbols):
                raise ValueError(f"Command '{command}' contains forbidden symbols.")
            # Ensure command starts with one of the allowed commands
            if not any(command.startswith(allowed_cmd) for allowed_cmd in allowed_commands):
                raise ValueError(f"Command '{command}' at path '{path}' is not allowed.")
       
        return v
