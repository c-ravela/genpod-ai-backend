from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

from database.database import Database
from database.entities.application_llm_metrics import ApplicationLLMMetrics
from utils.logger import logger


class ApplicationLLMMetricsService:
    """
    Service class for managing ApplicationLLMMetricsService operations.
    """

    def __init__(self):
        logger.debug("Initializing ApplicationLLMMetricsService.")
        try:
            self.db_session = Database.get_db_session()
            logger.info("ApplicationLLMMetricsService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ApplicationLLMMetricsService: {e}")
            raise

    def create_token_metrics(self, token_metrics: ApplicationLLMMetrics) -> None:
        """
        Creates a new application token metric record in the database.
        """
        logger.info(f"Creating application token metric: {token_metrics}")
        try:
            self.db_session.add(token_metrics)
            self.db_session.commit()
            logger.info(f"Application token metric created successfully: {token_metrics}")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error creating application token metric: {e}")
            raise
    
    def get_token_metrics_by_id(self, token_metrics_id: int) -> Optional[ApplicationLLMMetrics]:
        """
        Retrieves a application token metric by its ID.
        """
        logger.info(f"Retrieving application token metric with ID: {token_metrics_id}")
        try:
            token_metrics = self.db_session.query(ApplicationLLMMetrics).filter(ApplicationLLMMetrics.id == token_metrics_id).first()
            if token_metrics:
                logger.info(f"Application token metric retrieved successfully: {token_metrics}")
            else:
                logger.warning(f"No application token metric found with ID: {token_metrics_id}")
            return token_metrics
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving application token metric with ID {token_metrics_id}: {e}")
            raise

    def update_token_metrics(self, updated_token_metrics: ApplicationLLMMetrics) -> Optional[ApplicationLLMMetrics]:
        """
        Updates an existing application token metric record.
        """
        logger.info(f"Updating application token metric with ID: {updated_token_metrics.id}")
        try:
            existing_token_metrics = self.get_token_metrics_by_id(updated_token_metrics.id)
            if not existing_token_metrics:
                logger.warning(f"No token metrics found with ID: {updated_token_metrics.id} to update.")
                return None

            updateable_fields = {
                'input_tokens',
                'output_tokens',
                'total_tokens',
                'llm_duration',
                'prompt_duration',
                'updated_by'
            }

            for field in updateable_fields:
                new_value = getattr(updated_token_metrics, field, None)
                if new_value is not None:
                    setattr(existing_token_metrics, field, new_value)

            self.db_session.commit()
            self.db_session.refresh(existing_token_metrics)
            logger.info(f"Application token metric updated successfully: {existing_token_metrics}")
            return existing_token_metrics
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error updating application token metric with ID {updated_token_metrics.id}: {e}")
            raise
    
    def delete_token_metrics(self, token_metrics_id: int) -> bool:
        """
        Deletes a application token metric.
        """
        logger.info(f"Deleting application token metric with ID: {token_metrics_id}")
        try:
            token_metrics = self.get_token_metrics_by_id(token_metrics_id)
            if not token_metrics:
                logger.warning(f"No application token metric found with ID: {token_metrics_id} to delete.")
                return False

            self.db_session.delete(token_metrics)
            self.db_session.commit()
            logger.info(f"Application token metric with ID {token_metrics_id} deleted successfully.")
            return True
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error deleting application token metric with ID {token_metrics_id}: {e}")
            raise

    def get_token_metrics_by_application_id(self, application_id: int, project_id: int, user_id: int) -> List[ApplicationLLMMetrics]:
        """
        Retrieves all application token metrics for a specific application.
        """
        logger.info(f"Retrieving application token metrics for application ID: {application_id}")
        try:
            token_metrics = self.db_session.query(ApplicationLLMMetrics).filter(
                ApplicationLLMMetrics.application_id == application_id,
                ApplicationLLMMetrics.project_id == project_id,
                ApplicationLLMMetrics.created_by == user_id
            ).all()
            logger.info(f"Retrieved {len(token_metrics)} token metrics for application ID {application_id}.")
            return token_metrics
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving token metrics for application ID {application_id}: {e}")
            raise
