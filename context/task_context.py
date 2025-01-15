from dataclasses import dataclass
from typing import Optional

@dataclass
class TaskContext:
    """Represents the context of a task with task-specific fields."""
    
    parent_task_id: Optional[str] = None
    task_id: str
