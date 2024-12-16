from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database.database_base import Base
from utils.logs.logging_utils import logger


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
    document_name = Column(String, nullable=False)
    page_number = Column(Integer, nullable=False)
    line_number = Column(Integer, nullable=False)
    size_of_data = Column(Integer, nullable=False)
    question = Column(String, nullable=False)
    response = Column(String, nullable=False)
    created_by = Column(Integer, nullable=False)
    updated_by = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="rag_analytics")
    microservice = relationship("Microservice", back_populates="rag_analytics")
    session = relationship("MicroserviceSession", back_populates="rag_analytics")

    def __init__(
        self,
        agent_id: str = None,
        project_id: int = None,
        microservice_id: int = None,
        session_id: int = None,
        task_id: str = None,
        document_name: str = None,
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
        logger.debug("Initializing RAGAnalytics entity.")
        self.agent_id = agent_id
        self.project_id = project_id
        self.microservice_id = microservice_id
        self.session_id = session_id
        self.task_id = task_id
        self.document_name = document_name
        self.page_number = page_number
        self.line_number = line_number
        self.size_of_data = size_of_data
        self.question = question
        self.response = response
        self.created_by = created_by
        self.updated_by = updated_by
        self.created_at = created_at
        self.updated_at = updated_at
        logger.info(f"RAGAnalytics entity initialized: {self}")

    def __repr__(self):
        logger.debug(f"Creating string representation for RAGAnalytics(id={self.id}).")
        return (
            f"<RAGAnalytics(id={self.id}, agent_id={self.agent_id}, project_id={self.project_id}, "
            f"microservice_id={self.microservice_id}, session_id={self.session_id}, task_id={self.task_id}, "
            f"document_name={self.document_name}, page_number={self.page_number}, "
            f"line_number={self.line_number}, size_of_data={self.size_of_data}, question={self.question}, "
            f"response={self.response}, created_at={self.created_at}, updated_at={self.updated_at})>"
        )
