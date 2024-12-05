from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database.database_base import Base
from utils.logs.logging_utils import logger


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
        logger.debug("Initializing TokenUsage entity.")
        self.project_id = project_id
        self.microservice_id = microservice_id
        self.agent_id = agent_id
        self.provider = provider
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by = created_by
        self.updated_by = updated_by
        logger.info(f"TokenUsage entity initialized: {self}")

    def __repr__(self):
        logger.debug(f"Creating string representation for TokenUsage(id={self.id}).")
        return (
            f"<TokenUsage(id={self.id}, project_id={self.project_id}, agent_id={self.agent_id}, "
            f"microservice_id={self.microservice_id}, provider={self.provider}, model={self.model}, "
            f"input_tokens={self.input_tokens}, output_tokens={self.output_tokens}, total_tokens={self.total_tokens}, "
            f"created_at={self.created_at}, updated_at={self.updated_at}, created_by={self.created_by}, "
            f"updated_by={self.updated_by})>"
        )
