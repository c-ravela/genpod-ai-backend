from dataclasses import dataclass
from typing import Optional


@dataclass
class TaskContext:
    """Represents the context of a task with task-specific fields."""
    
    task_id: str
    parent_task_id: Optional[str] = None
