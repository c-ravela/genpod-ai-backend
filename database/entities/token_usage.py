from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database.database_base import Base
from utils.decorators import auto_init


class TokenUsage(Base):
    """
    Represents the 'microservice_token_usage' table in the database.
    """
    __tablename__ = 'microservice_token_usage'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    microservice_id = Column(Integer, ForeignKey('microservices.id'), nullable=False)
    agent_id = Column(String(255), nullable=False)
    provider = Column(String(255), nullable=False)  # LLM provider name
    model = Column(String(255), nullable=False)  # LLM model name/version
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    created_by = Column(Integer, nullable=False)
    updated_by = Column(Integer, nullable=False)

    project = relationship("Project", back_populates="token_metrics")
    microservice = relationship("Microservice", back_populates="token_metrics")

    @auto_init
    def __init__(
        self,
        project_id: int = None,
        microservice_id: int = None,
        agent_id: str = None,
        provider: str = None,
        model: str = None,
        input_tokens: int = None,
        output_tokens: int = None,
        total_tokens: int = None,
        created_by: int = None,
        updated_by: int = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        pass
