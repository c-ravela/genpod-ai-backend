from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from database.database_base import Base
from utils.logs.logging_utils import logger


class Project(Base):
    """
    Represents the 'projects' table in the database.
    """

    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(255), nullable=False)
    project_description = Column(String(255), nullable=True)
    created_by = Column(Integer, nullable=False)
    updated_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    microservice = relationship("Microservice", back_populates="project", cascade="all, delete-orphan")
    microservice_sessions = relationship("MicroserviceSession", back_populates="project", cascade="all, delete-orphan")
    token_metrics = relationship("TokenUsage", back_populates="project", cascade="all, delete-orphan")
    rag_analytics = relationship("RAGAnalytics", back_populates="project", cascade="all, delete-orphan")

    def __init__(
        self,
        id: int = None,
        project_name: str = None,
        project_description: str = None,
        created_by: int = None,
        updated_by: int = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        logger.debug("Initializing Project entity.")
        self.id = id
        self.project_name = project_name
        self.project_description = project_description
        self.created_by = created_by
        self.updated_by = updated_by
        self.created_at = created_at
        self.updated_at = updated_at
        logger.info(f"Project entity initialized: {self}")

    def __repr__(self):
        logger.debug(f"Creating string representation for Project(id={self.id}).")
        
        return (
            f"<Project(id={self.id}, project_name={self.project_name}, "
            f"project_description={self.project_description}, "
            f"created_by={self.created_by}, updated_by={self.updated_by}, "
            f"created_at={self.created_at}, updated_at={self.updated_at})>"
        )
