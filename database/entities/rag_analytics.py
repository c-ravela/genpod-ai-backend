from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database.database_base import Base
from utils.decorators import auto_init


class RAGAnalytics(Base):
    """
    Represents the 'rag_analytics' table in the database.
    """
    __tablename__ = 'rag_analytics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(255), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    microservice_id = Column(Integer, ForeignKey('microservices.id'), nullable=False)
    session_id = Column(Integer, ForeignKey('microservice_sessions.id'), nullable=False)
    task_id = Column(String, nullable=False)
    document_id = Column(String, nullable=True)
    document_name = Column(String, nullable=True)
    document_version = Column(String, nullable=True)
    raw_respone = Column(String, nullable=False)
    page_number = Column(Integer, nullable=True)
    line_number = Column(Integer, nullable=True)
    size_of_data = Column(Integer, nullable=True)
    question = Column(String, nullable=False)
    response = Column(String, nullable=True)
    created_by = Column(Integer, nullable=False)
    updated_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="rag_analytics")
    microservice = relationship("Microservice", back_populates="rag_analytics")
    session = relationship("MicroserviceSession", back_populates="rag_analytics")

    @auto_init
    def __init__(
        self,
        id: int = None,
        agent_id: str = None,
        project_id: int = None,
        microservice_id: int = None,
        session_id: int = None,
        task_id: str = None,
        document_id: String = None,
        document_name: str = None,
        document_version: str = None,
        raw_respone: str = None,
        page_number: int = None,
        line_number: int = None,
        size_of_data: int = None,
        question: str = None,
        response: str = None,
        created_by: int = None,
        updated_by: int = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):  
        pass
