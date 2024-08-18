"""
This module, `models.py`, contains various data models used throughout the project.

Each class in this module represents a different data model, with each model 
capturing a specific set of information required for the project. These models
are used to structure the data in a consistent and organized manner, enhancing 
the readability and maintainability of the code.
"""
from typing import Any

from pydantic import BaseModel, Field

from models.constants import Status
from utils.task_utils import generate_task_id


class Task(BaseModel):
    """
    A data model representing a task and its current state within a project
    or workflow.
    """
    task_id: str = Field(
        description="A unique task id to track and access current task and previous tasks",
        default_factory=generate_task_id
    )

    description: str = Field(
        description="A brief description outlining the objective of the task",
        default="",
        required=True
    )

    task_status: Status = Field(
        description="The current status indicating the progress of the task",
        default= Status.NONE,
        required=True
    )

    additional_info: str = Field(
        description="Additional info requested.",
        default=""
    )

    question: str = Field(
        description="Question to supervisor if additional information is needed"
        " to proceed with task execution.",
        default=""
    )

    remarks: str = Field(
        description="A field for notes on the task's status. If the task is "
        "abandoned, state the reason here.",
        default=""
    )

class RequirementsDocument(BaseModel):
    """
    This class encapsulates the various requirements of a project. 
    """

    project_overview: str = Field(
        description="A brief overview of the project.",
        default=""
    )
    
    project_architecture: str = Field(
        description="Detailed information about the project's architecture.",
        default=""
    )

    directory_structure: str = Field(
        description="A description of the project's directory and folder structure.",
        default=""
    )

    microservices_architecture: str = Field(
        description="Details about the design and architecture of the project's microservices.",
        default=""
    )

    tasks_overview: str = Field(
        description="An overview of the tasks involved in the project.",
        default=""
    )

    coding_standards: str = Field(
        description="The coding standards and conventions followed in the project.",
        default=""
    )

    implementation_process: str = Field(
        description="A detailed description of the implementation process.",
        default=""
    )

    project_license_information: str = Field(
        description="Information about the project's licensing terms and conditions.",
        default=""
    )

    def to_markdown(self) -> str:
        """
        Generates a Markdown-formatted requirements document for the project.

        Returns:
            str: A Markdown string representing the requirements document.
        """

        return f"""
# Project Requirements Document

## Project Overview
{self.project_overview}

## Project Architecture
{self.project_architecture}

## Directory Structure
{self.directory_structure}

## Microservices Architecture
{self.microservices_architecture}

## Tasks Overview
{self.tasks_overview}

## Coding Standards
{self.coding_standards}

## Implementation Process
{self.implementation_process}

## Project License Information
{self.project_license_information}
        """
    
    def __getitem__(self, key: str) -> Any:
        """
        Allows getting attributes using square bracket notation.
        """
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"Key '{key}' not found in RequirementsDocument.")

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Allows setting attributes using square bracket notation.
        """
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise KeyError(f"Key '{key}' not found in RequirementsDocument.")