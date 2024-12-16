from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

from database.database import Database
from database.entities.rag_analytics import RAGAnalytics
from utils.logs.logging_utils import logger


class RAGAnalyticsService:
    """
    Service class for managing RAGAnalytics operations.
    """

    def __init__(self):
        logger.debug("Initializing RAGAnalyticsService.")
        try:
            self.db_session = Database.get_db_session()
            logger.info("RAGAnalyticsService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize RAGAnalyticsService: {e}")
            raise

    def create_analytics(self, analytics: RAGAnalytics) -> None:
        """
        Creates a new RAG analytics record in the database.

        Args:
            analytics (RAGAnalytics): The RAGAnalytics instance to be created.
        """
        logger.info(f"Creating RAG analytics record: {analytics}")
        try:
            self.db_session.add(analytics)
            self.db_session.commit()
            logger.info(f"RAG analytics record created successfully: {analytics}")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error creating RAG analytics record: {e}")
            raise

    def get_analytics_by_id(self, analytics_id: int) -> Optional[RAGAnalytics]:
        """
        Retrieves a RAG analytics record by its ID.

        Args:
            analytics_id (int): The ID of the RAG analytics record.

        Returns:
            Optional[RAGAnalytics]: The RAGAnalytics instance if found, else None.
        """
        logger.info(f"Retrieving RAG analytics record with ID: {analytics_id}")
        try:
            analytics = self.db_session.query(RAGAnalytics).filter(RAGAnalytics.id == analytics_id).first()
            if analytics:
                logger.info(f"RAG analytics record retrieved successfully: {analytics}")
            else:
                logger.warning(f"No RAG analytics record found with ID: {analytics_id}")
            return analytics
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving RAG analytics record with ID {analytics_id}: {e}")
            raise

    def update_analytics(self, updated_analytics: RAGAnalytics) -> Optional[RAGAnalytics]:
        """
        Updates an existing RAG analytics record.

        Args:
            updated_analytics (RAGAnalytics): The updated RAGAnalytics instance.

        Returns:
            Optional[RAGAnalytics]: The updated RAGAnalytics instance if successful, else None.
        """
        logger.info(f"Updating RAG analytics record with ID: {updated_analytics.id}")
        try:
            existing_analytics = self.get_analytics_by_id(updated_analytics.id)
            if not existing_analytics:
                logger.warning(f"No RAG analytics record found with ID: {updated_analytics.id} to update.")
                return None

            updateable_fields = {
                'agent_id',
                'project_id',
                'microservice_id',
                'session_id',
                'task_id',
                'document_name',
                'page_number',
                'line_number',
                'size_of_data',
                'question',
                'response',
                'updated_by',
            }

            for field in updateable_fields:
                new_value = getattr(updated_analytics, field, None)
                if new_value is not None:
                    setattr(existing_analytics, field, new_value)

            self.db_session.commit()
            self.db_session.refresh(existing_analytics)
            logger.info(f"RAG analytics record updated successfully: {existing_analytics}")
            return existing_analytics
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error updating RAG analytics record with ID {updated_analytics.id}: {e}")
            raise

    def delete_analytics(self, analytics_id: int) -> bool:
        """
        Deletes a RAG analytics record.

        Args:
            analytics_id (int): The ID of the RAG analytics record to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        logger.info(f"Deleting RAG analytics record with ID: {analytics_id}")
        try:
            analytics = self.get_analytics_by_id(analytics_id)
            if not analytics:
                logger.warning(f"No RAG analytics record found with ID: {analytics_id} to delete.")
                return False

            self.db_session.delete(analytics)
            self.db_session.commit()
            logger.info(f"RAG analytics record with ID {analytics_id} deleted successfully.")
            return True
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error deleting RAG analytics record with ID {analytics_id}: {e}")
            raise

    def get_analytics_by_session(self, session_id: int) -> List[RAGAnalytics]:
        """
        Retrieves all RAG analytics records for a specific session.

        Args:
            session_id (int): The ID of the session.

        Returns:
            List[RAGAnalytics]: A list of RAGAnalytics instances.
        """
        logger.info(f"Retrieving RAG analytics records for session ID: {session_id}")
        try:
            analytics_records = self.db_session.query(RAGAnalytics).filter(
                RAGAnalytics.session_id == session_id
            ).all()
            logger.info(f"Retrieved {len(analytics_records)} RAG analytics records for session ID: {session_id}")
            return analytics_records
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving RAG analytics records for session ID {session_id}: {e}")
            raise
