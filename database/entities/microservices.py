from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database.database_base import Base
from utils.decorators import auto_init


class Microservice(Base):
    """
    Represents the 'microservices' table in the database.
    """

    __tablename__ = 'microservices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    microservice_name = Column(String(255), nullable=True)
    microservice_description = Column(String(500), nullable=True)
    prompt = Column(String, nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    status = Column(String(50), nullable=False)
    license_text = Column(String, nullable=True)
    license_file_url = Column(String, nullable=True)
    project_location = Column(String, nullable=False)
    created_by = Column(Integer, nullable=False)
    updated_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="microservice")
    sessions = relationship("MicroserviceSession", back_populates="microservice", cascade="all, delete-orphan")
    token_metrics = relationship("TokenUsage", back_populates="microservice", cascade="all, delete-orphan")
    rag_analytics = relationship("RAGAnalytics", back_populates="microservice", cascade="all, delete-orphan")

    @auto_init
    def __init__(
        self,
        id: int = None,
        microservice_name: str = None,
        microservice_description: str = None,
        prompt: str = None,
        project_id: int = None,
        status: str = None,
        license_text: str = None,
        license_file_url: str = None,
        project_location: str = None,
        created_by: int = None,
        updated_by: int = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        pass
