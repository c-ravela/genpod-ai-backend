
from typing import List, Tuple

from pydantic import BaseModel

from core.state import IState
from models.constants import ChatRoles


class BaseState(BaseModel, IState):
    """
    Base class for agent states, implementing common functionalities.
    """

    messages: List[Tuple[ChatRoles, str]] = []

