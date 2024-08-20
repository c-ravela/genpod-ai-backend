"""
This module defines the data model for the output of the TestGenerator agent. 

The TestGenerator agent is responsible for completing tasks in a project. The output of 
the TestGenerator agent includes information about the steps to complete a task, 
the files to be created, the location of the code, the actual code.
"""

from pydantic import BaseModel, Field


class FunctionSkeletonFields(BaseModel):
    """
    """
    
    function_name: str= Field(
        description="""
        A concise and descriptive name for the function.""", required=True
    )

    input_params: list[str] =Field(
        description="""
        A list of input parameters the function will take, including their types and descriptions""", required=True
    )

    return_type: list[str] = Field(
        description="""
        A description of the function's output, including its type and what it represents""",required=True 
    )

    function_description: str = Field(
        description="""
        A comprehensive description of what the function needs to do and how it should achieve its goal.""", required=True
    )


class FunctionSkeleton(BaseModel):
    """
    """
    skeletons_to_create: dict[str, FunctionSkeletonFields] = Field(
        description="""
        A dictionary where each key-value pair represents a file and its corresponding function skeleton. The key 
        should be the absolute path to the file, and the value should be the well-descriptive function skeleton
          for that particular file.
        """, 
        required=True
    )

