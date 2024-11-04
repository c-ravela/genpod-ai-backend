"""
This module, `models.py`, contains various data models used throughout the project.

Each class in this module represents a different data model, with each model
capturing a specific set of information required for the project. These models
are used to structure the data in a consistent and organized manner, enhancing
the readability and maintainability of the code.
"""
from typing import Any, Generic, Iterator, List, Optional, TypeVar

from pydantic import BaseModel, Field

from models.constants import Status
from models.tests_generator_models import FileFunctionSignatures
from utils.task_utils import generate_task_id

QueueType = TypeVar("QueueType", bound=BaseModel)
TQueue = TypeVar('TQueue', bound='Queue')


class Queue(BaseModel, Generic[QueueType]):
    """
    A base class to manage a queue of items with an index to keep track of the next
    item to process.
    """

    next: int = Field(
        description="Index of the next item to process",
        default=0
    )

    items: List[QueueType] = Field(
        description="List of items in the queue",
        default=[]
    )

    def add_item(self, item: QueueType) -> None:
        """
        Adds a new item to the end of the queue.

        Args:
            item (QueueType): The item to be added.
        """
        self.items.append(item)

    def extend(self: TQueue, queue: TQueue) -> None:
        """
        Extends the current queue with the items from another queue of the same type.

        Args:
            other (TQueue): Another instance of the same Queue subclass.
        """
        self.items.extend(queue)

    def get_next_item(self) -> Optional[QueueType]:
        """
        Retrieves and advances to the next item in the queue.

        Returns:
            Optional[QueueType]: The next item in the queue, or None if no items are
            left.
        """
        if self.next < len(self.items):
            item = self.items[self.next]
            self.next += 1
            return item

        return None

    def get_all_items(self) -> List[QueueType]:
        """
        Returns a list of all items in the queue.

        Returns:
            List[QueueType]: A list containing all items in the queue.
        """
        return self.items

    def update_item(self, updated_item: QueueType) -> None:
        """
        Updates an existing item in the queue with the new values from the updated_item.

        This method must be implemented by subclasses.

        Args:
            updated_item (QueueType): The updated item with new values.

        Raises:
            NotImplementedError: If this method is not overridden in a subclass.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def has_pending_items(self) -> bool:
        """
        Checks if there are any pending items that have not yet been processed.

        Returns:
            bool: True if there are unprocessed items, False otherwise.
        """
        return self.next < len(self.items)

    def __str__(self) -> str:
        """
        Returns a string representation of the Queue.

        Returns:
            str: A string representing the current items and the index of the next item.
        """
        return f"Items: {self.items}, Next Index: {self.next}"

    def __iter__(self) -> Iterator[QueueType]:
        """
        Returns an iterator over the items in the queue.

        Returns:
            Iterator[QueueType]: An iterator for the items in the queue.
        """
        return iter(self.items)

    def __len__(self) -> int:
        """
        Returns the number of items in the queue.

        Returns:
            int: The number of items in the queue.
        """
        return len(self.items)


class Task(BaseModel):
    """
    A data model representing a task and its current state within a project
    or workflow.
    """

    task_id: str = Field(
        description=(
            "A unique task id to track and access current task and previous "
            "tasks"
        ),
        default_factory=generate_task_id
    )

    task_status: Status = Field(
        description="The current status indicating the progress of the task",
        default=Status.NONE,
        required=True
    )

    description: str = Field(
        description="A brief description outlining the objective of the task",
        default="",
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


class TaskQueue(Queue[Task]):
    """A queue specifically for Task objects."""

    def update_item(self, updated_task: Task) -> None:
        """
        Updates an existing task in the queue with the new values from the updated_task.

        Args:
            updated_task (Task): The updated Task object with new values.

        Raises:
            ValueError: If the task to be updated is not found in the queue.
        """
        for i, task in enumerate(self.items):
            if task.task_id == updated_task.task_id:
                self.items[i] = updated_task
                return
        raise ValueError(f"Task with ID {updated_task.task_id} not found in the queue.")


class PlannedTask(BaseModel):
    """
    A data model representing a task and its current state within a project
    or workflow.
    """

    parent_task_id: str = Field(
        description="A unique task id representing it parent task id",
        default=""
    )

    task_id: str = Field(
        description=(
            "A unique task id to track and access current task and previous"
            "tasks"
        ),
        default_factory=generate_task_id
    )

    task_status: Status = Field(
        description="The current status indicating the progress of the task",
        default=Status.NONE,
        required=True
    )

    # if this is True then test code has to be generated first
    # then code has to be generated.
    is_function_generation_required: bool = Field(
        description="whether the current task involves writing code.",
        default=False,
        required=True
    )

    is_test_code_generated: bool = Field(
        description="unit test cases generated or not for this task",
        default=False,
    )

    is_code_generated: bool = Field(
        description="funtional code is generated or not",
        default=False
    )

    description: str = Field(
        description="A brief description outlining the objective of the task",
        default="",
        required=True
    )


class PlannedTaskQueue(Queue[PlannedTask]):
    """A queue specifically for PlannedTask objects."""

    def update_item(self, updated_task: PlannedTask) -> None:
        """
        Updates an existing planned task in the queue with the new values from the
        updated_task.

        Args:
            updated_task (PlannedTask): The updated PlannedTask object with new values.

        Raises:
            ValueError: If the planned task to be updated is not found in the queue.
        """
        for i, task in enumerate(self.items):
            if task.task_id == updated_task.task_id:
                self.items[i] = updated_task
                return

        raise ValueError(
            f"PlannedTask with ID {updated_task.task_id} not found in the queue."
        )


class Issue(BaseModel):
    """
    A model representing an issue with various attributes including status, description,
    and file path.
    """

    issue_id: str = Field(
        description="A unique identifier for the issue.",
        default_factory=generate_task_id
    )

    issue_status: Status = Field(
        description="The current status of the issue.",
        default=Status.NONE,
        required=True
    )

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
        examples=[
            "Define the variable 'x' before use",
            "Check variable scope and initialization"
        ]
    )

    def issue_details(self) -> str:
        """Return a formatted string representing the actual issue details."""
        details = f"Issue: {self.description}\n"
        details += f"File: {self.file_path}\n"

        if self.line_number:
            details += f"Line: {self.line_number}\n"

        if self.suggestions:
            suggestions_str = "\n".join(self.suggestions)
            details += f"Suggestions:\n{suggestions_str}\n"

        return details


class IssuesQueue(Queue[Issue]):
    """
    A specialized queue for managing issues, allowing updates to existing
    issues within the queue.
    """

    def update_item(self, updated_issue: Issue) -> None:
        """
        Update an existing issue in the queue with the provided updated issue.

        Args:
            updated_issue (Issue): The updated issue to replace the existing
            issue in the queue.

        Raises:
            ValueError: If the issue with the specified ID is not found in the
            queue.
        """
        for i, issue in enumerate(self.items):
            if issue.issue_id == updated_issue.issue_id:
                self.items[i] = updated_issue
                return
        raise ValueError(f"Issue with ID {updated_issue.issue_id} not found in the "
                         "queue.")


class PlannedIssue(BaseModel):
    parent_id: str = Field(
        description="The identifier of the parent issue, if any.",
        default=""
    )

    id: str = Field(
        description="A unique identifier for the issue.",
        default_factory=generate_task_id
    )

    status: Status = Field(
        description="The current status of the issue.",
        default=Status.NONE,
    )

    is_function_generation_required: bool = Field(
        description="Whether the current task involves writing code.",
        required=True
    )

    is_test_code_generated: bool = Field(
        description="Indicates whether unit test cases have been generated for this "
                    "task.",
        default=False
    )

    is_code_generated: bool = Field(
        description="Indicates whether the functional code has been generated.",
        default=False
    )

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

    suggestions: List[str] = Field(
        default=[],
        description="Suggestions for resolving the issue.",
        title="Suggestions",
        examples=[
            "Define the variable 'x' before use",
            "Check variable scope and initialization"
        ]
    )

    function_signatures: FileFunctionSignatures = Field(
        description="The skeleton or template of the function that needs to be "
                    "implemented.",
        default=FileFunctionSignatures(function_signatures={}),
        examples=["def function_name(args): pass"]
    )

    test_code: dict[str, str] = Field(
        description="The generated unit test code for the function.",
        default={},
        examples=["def test_function_name(): assert function_name() == expected_output"]
    )

    def issue_details(self) -> str:
        """Return a formatted string representing the actual issue details."""
        details = f"Issue: {self.description}\n"
        details += f"File: {self.file_path}\n"

        if self.line_number:
            details += f"Line: {self.line_number}\n"

        if self.suggestions:
            suggestions_str = "\n".join(self.suggestions)
            details += f"Suggestions:\n{suggestions_str}\n"

        return details


class PlannedIssuesQueue(Queue[PlannedIssue]):
    """
    A specialized queue for managing issues, allowing updates to existing issues
    within the queue.
    """

    def update_item(self, updated_issue: PlannedIssue) -> None:
        """
        Update an existing issue in the queue with the provided updated issue.

        Args:
            updated_issue (PlannedIssue): The updated issue to replace the existing
            issue in the queue.

        Raises:
            ValueError: If the issue with the specified ID is not found in the queue.
        """
        for i, issue in enumerate(self.items):
            if issue.id == updated_issue.id:
                self.items[i] = updated_issue
                return
        raise ValueError(f"Issue with ID {updated_issue.id} not found in the queue.")


class RequirementsDocument(BaseModel):
    """
    Represents a comprehensive document that encapsulates the various
    requirements of a project. This class includes details about the
    project's architecture, tasks, coding standards, implementation
    process, and licensing information. It also provides methods to
    generate a Markdown representation of the document.
    """

    project_overview: str = Field(
        description="A brief overview of the project, summarizing its goals "
                    "and objectives.",
        default=""
    )

    project_architecture: str = Field(
        description="Detailed information about the project's architecture, "
                    "including design patterns and key components.",
        default=""
    )

    directory_structure: str = Field(
        description="A description of the project's directory and folder "
                    "structure, outlining the organization of files and "
                    "directories.",
        default=""
    )

    microservices_architecture: str = Field(
        description="Details about the design and architecture of the "
                    "project's microservices, including their interactions "
                    "and dependencies.",
        default=""
    )

    tasks_overview: str = Field(
        description="An overview of the tasks involved in the project, "
                    "including their purpose and key objectives.",
        default=""
    )

    coding_standards: str = Field(
        description="The coding standards and conventions followed in the "
                    "project, ensuring consistency and quality in the "
                    "codebase.",
        default=""
    )

    implementation_process: str = Field(
        description="A detailed description of the implementation process, "
                    "including phases, milestones, and methodologies.",
        default=""
    )

    project_license_information: str = Field(
        description="Information about the project's licensing terms and "
                    "conditions, including usage rights and restrictions.",
        default=""
    )

    def to_markdown(self) -> str:
        """
        Generates a Markdown-formatted string representing the requirements
        document.

        Returns:
            str: A Markdown string that represents the requirements document,
            formatted with sections for each attribute.
        """

        return f"""
# Project Requirements Document

{self.project_overview}

{self.project_architecture}

{self.directory_structure}

{self.microservices_architecture}

{self.tasks_overview}

{self.coding_standards}

{self.implementation_process}

{self.project_license_information}
        """

    def __getitem__(self, key: str) -> Any:
        """
        Retrieves the value of an attribute using square bracket notation.

        Args:
            key (str): The name of the attribute to retrieve.

        Returns:
            Any: The value of the specified attribute.

        Raises:
            KeyError: If the attribute with the specified key does not exist 
            in the document.
        """
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"Key '{key}' not found in RequirementsDocument.")

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Sets the value of an attribute using square bracket notation.

        Args:
            key (str): The name of the attribute to set.
            value (Any): The new value to assign to the specified attribute.

        Raises:
            KeyError: If the attribute with the specified key does not exist 
            in the document.
        """
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise KeyError(f"Key '{key}' not found in RequirementsDocument.")
