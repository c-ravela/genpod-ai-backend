from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database.database_base import Base
from utils.decorators import auto_init


class ApplicationSession(Base):
    """
    Represents the 'application_sessions' table in the database.
    """

    __tablename__ = 'application_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(255), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False)
    created_by = Column(Integer, nullable=False)
    updated_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="application_sessions")
    application = relationship("Application", back_populates="sessions")
    rag_analytics = relationship("RAGAnalytics", back_populates="session", cascade="all, delete-orphan")

    @auto_init
    def __init__(
        self,
        id: int = None,
        agent_id: str = None,
        project_id: int = None,
        application_id: int = None,
        created_by: int = None,
        updated_by: int = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        pass
