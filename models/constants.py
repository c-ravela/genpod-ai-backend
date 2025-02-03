"""
This `enums.py` module contains various enumerations used throughout the project. 
These enumerations provide a systematic way to represent distinct values and 
categories using symbolic names, enhancing the readability and maintainability 
of the code. Each enumeration is defined as a separate class and can be imported 
for use in other modules.
"""
from enum import Enum


class ChatRoles(Enum):
    """
    An enumeration representing the various roles in a chat conversation with 
    the Language Learning Model (LLM) using the ChatPromptTemplate.

    This class is used to categorize the messages in the graph state according 
    to the role of the sender. The roles include 'assistant' (AI), 'tool', 
    'user', and 'system'. These roles help in identifying who sent a particular 
    message or performed a certain action in the conversation.

    Attributes:
        AI (str): Represents the assistant's role in the conversation.
        TOOL (str): Represents the tool's role in the conversation.
        USER (str): Represents the user's role in the conversation.
        SYSTEM (str): Represents the system's role in the conversation.
    """

    AI: str = "assistant"
    TOOL: str = "tool"
    USER: str = "user"
    SYSTEM: str = "system"

    def __str__(self):
      """
      Returns the string representation of the Enum member.

      Returns:
          str: The value of the Enum member.
      """
      return self.value
    
class Status(Enum):
    """
    Enumeration representing the states of a task or project.

    States:
    - 'NONE': No status assigned.
    - 'NEW': Initial state.
    - 'AWAITING': Waiting for an event or dependency.
    - 'RESPONDED': Response received after being in 'AWAITING'.
    - 'INPROGRESS': Currently being worked on.
    - 'ABANDONED': Left incomplete.
    - 'DONE': Completed.
    """
    
    NONE = "NONE"
    NEW = "NEW"
    AWAITING = "AWAITING"
    RESPONDED = "RESPONDED"
    INPROGRESS = "INPROGRESS"
    ABANDONED = "ABANDONED"
    DONE = "DONE"

    def __str__(self):
        """
        Returns the string representation of the Enum member.

        Returns:
            str: The value of the Enum member.
        """
        return self.value

class PStatus(Enum):
    """
    Enumeration representing the various states a project can be in.
    
    Each member of this enum corresponds to a specific phase in a project's lifecycle.
    
    The states track the project's progress through different phases:

    - 'NONE': No status has been assigned to the project yet.
    - 'RECEIVED': The project has been received but not yet processed.
    - 'NEW': The project is in the pre-initiation phase.
    - 'INITIAL': Setup is pending; initial preparations are underway.
    - 'EXECUTING': The assigned task is currently in progress.
    - 'MONITORING': The project is being monitored for any issues during execution.
    - 'REVIEWING': The project is under review, often for quality control or feedback.
    - 'RESOLVING': Issues have been identified and are being addressed or resolved.
    - 'HALTED': The project is paused, either due to completion or because of unresolved issues requiring intervention.
    - 'DONE': All user-requested requirements have been fulfilled, and the project is complete.
    """

    NONE: str = "NONE"
    RECEIVED: str = "RECEIVED"
    NEW: str = "NEW"
    INITIAL: str = "INITIAL"
    EXECUTING: str = "EXECUTING"
    MONITORING: str = "MONITORING"
    REVIEWING: str = "REVIEWING"
    RESOLVING: str = "RESOLVING"
    HALTED: str = "HALTED"
    DONE: str = "DONE"

    def __str__(self):
      """
      Returns the string representation of the Enum member.

      Returns:
          str: The value of the Enum member.
      """
      return self.value
