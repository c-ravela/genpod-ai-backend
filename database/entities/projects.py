from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from database.database_base import Base
from utils.decorators import auto_init


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

    @auto_init
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
        pass
