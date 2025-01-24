from abc import ABC
from typing import List, Tuple

from pydantic import BaseModel

from models.constants import ChatRoles


class IState(ABC, BaseModel):
    """
    Interface for all agent states.
    """

    messages: List[Tuple[ChatRoles, str]] = []

