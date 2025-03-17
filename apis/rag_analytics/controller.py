from typing import List, Optional

from apis.rag_analytics.service import RAGAnalyticsService
from database.entities.rag_analytics import RAGAnalytics
from utils.logs.logging_utils import logger


class RAGAnalyticsController:
    """
    Controller class for handling RAGAnalytics-related operations.
    """

    def __init__(self):
        logger.debug("Initializing RAGAnalyticsController.")
        self.rag_analytics_service = RAGAnalyticsService()
        logger.info("RAGAnalyticsController initialized successfully.")

    def create(self, analytics: RAGAnalytics) -> None:
        """
        Creates a new RAG analytics record.
        """
        logger.info(f"Creating a new RAG analytics record: {analytics}")
        try:
            self.rag_analytics_service.create_analytics(analytics)
            logger.info(f"RAG analytics record created successfully: {analytics}")
        except Exception as e:
            logger.error(f"Failed to create RAG analytics record: {e}")
            raise

    def update(self, analytics: RAGAnalytics) -> Optional[RAGAnalytics]:
        """
        Updates an existing RAG analytics record.
        """
        logger.info(f"Updating RAG analytics record: {analytics}")
        try:
            updated_analytics = self.rag_analytics_service.update_analytics(analytics)
            if updated_analytics:
                logger.info(f"RAG analytics record updated successfully: {updated_analytics}")
            else:
                logger.warning(f"RAG analytics record update returned None: {analytics}")
            return updated_analytics
        except Exception as e:
            logger.error(f"Failed to update RAG analytics record: {e}")
            raise

    def delete(self, analytics_id: int) -> bool:
        """
        Deletes a RAG analytics record.
        """
        logger.info(f"Deleting RAG analytics record with ID: {analytics_id}")
        try:
            result = self.rag_analytics_service.delete_analytics(analytics_id)
            if result:
                logger.info(f"RAG analytics record with ID {analytics_id} deleted successfully.")
            else:
                logger.warning(f"RAG analytics record with ID {analytics_id} could not be deleted.")
            return result
        except Exception as e:
            logger.error(f"Failed to delete RAG analytics record with ID {analytics_id}: {e}")
            raise

    def get_analytics(self, analytics_id: int) -> Optional[RAGAnalytics]:
        """
        Retrieves a single RAG analytics record by ID.
        """
        logger.info(f"Retrieving RAG analytics record with ID: {analytics_id}")
        try:
            analytics = self.rag_analytics_service.get_analytics_by_id(analytics_id)
            if analytics:
                logger.info(f"RAG analytics record retrieved successfully: {analytics}")
            else:
                logger.warning(f"No RAG analytics record found with ID: {analytics_id}")
            return analytics
        except Exception as e:
            logger.error(f"Failed to retrieve RAG analytics record with ID {analytics_id}: {e}")
            raise

    def get_analytics_by_session(self, session_id: int) -> List[RAGAnalytics]:
        """
        Retrieves all RAG analytics records for a specific session.
        """
        logger.info(f"Retrieving RAG analytics records for session ID: {session_id}")
        try:
            analytics_records = self.rag_analytics_service.get_analytics_by_session(session_id)
            logger.info(f"Retrieved {len(analytics_records)} RAG analytics records for session ID: {session_id}")
            return analytics_records
        except Exception as e:
            logger.error(f"Failed to retrieve RAG analytics records for session ID {session_id}: {e}")
            raise
