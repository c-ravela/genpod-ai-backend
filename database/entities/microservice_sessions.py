from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database.database_base import Base
from utils.decorators import auto_init


class MicroserviceSession(Base):
    """
    Represents the 'microservice_sessions' table in the database.
    """

    __tablename__ = 'microservice_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(255), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    microservice_id = Column(Integer, ForeignKey('microservices.id'), nullable=False)
    created_by = Column(Integer, nullable=False)
    updated_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="microservice_sessions")
    microservice = relationship("Microservice", back_populates="sessions")
    rag_analytics = relationship("RAGAnalytics", back_populates="session", cascade="all, delete-orphan")

    @auto_init
    def __init__(
        self,
        id: int = None,
        agent_id: str = None,
        project_id: int = None,
        microservice_id: int = None,
        created_by: int = None,
        updated_by: int = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        pass
