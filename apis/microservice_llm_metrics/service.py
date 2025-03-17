from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

from database.database import Database
from database.entities.microservice_llm_metrics import MicroserviceLLMMetrics
from utils.logs.logging_utils import logger


class MicroserviceLLMMetricsService:
    """
    Service class for managing MicroserviceLLMMetrics operations.
    """

    def __init__(self):
        logger.debug("Initializing MicroserviceLLMMetricsService.")
        try:
            self.db_session = Database.get_db_session()
            logger.info("MicroserviceLLMMetricsService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MicroserviceLLMMetricsService: {e}")
            raise

    def create_token_metrics(self, token_metrics: MicroserviceLLMMetrics) -> None:
        """
        Creates a new microservice token metric record in the database.
        """
        logger.info(f"Creating microservice token metric: {token_metrics}")
        try:
            self.db_session.add(token_metrics)
            self.db_session.commit()
            logger.info(f"Microservice token metric created successfully: {token_metrics}")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error creating microservice token metric: {e}")
            raise
    
    def get_token_metrics_by_id(self, token_metrics_id: int) -> Optional[MicroserviceLLMMetrics]:
        """
        Retrieves a microservice token metric by its ID.
        """
        logger.info(f"Retrieving microservice token metric with ID: {token_metrics_id}")
        try:
            token_metrics = self.db_session.query(MicroserviceLLMMetrics).filter(MicroserviceLLMMetrics.id == token_metrics_id).first()
            if token_metrics:
                logger.info(f"Microservice token metric retrieved successfully: {token_metrics}")
            else:
                logger.warning(f"No microservice token metric found with ID: {token_metrics_id}")
            return token_metrics
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving microservice token metric with ID {token_metrics_id}: {e}")
            raise

    def update_token_metrics(self, updated_token_metrics: MicroserviceLLMMetrics) -> Optional[MicroserviceLLMMetrics]:
        """
        Updates an existing microservice token metric record.
        """
        logger.info(f"Updating microservice token metric with ID: {updated_token_metrics.id}")
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
            logger.info(f"Microservice token metric updated successfully: {existing_token_metrics}")
            return existing_token_metrics
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error updating microservice token metric with ID {updated_token_metrics.id}: {e}")
            raise
    
    def delete_token_metrics(self, token_metrics_id: int) -> bool:
        """
        Deletes a microservice token metric.
        """
        logger.info(f"Deleting microservice token metric with ID: {token_metrics_id}")
        try:
            token_metrics = self.get_token_metrics_by_id(token_metrics_id)
            if not token_metrics:
                logger.warning(f"No microservice token metric found with ID: {token_metrics_id} to delete.")
                return False

            self.db_session.delete(token_metrics)
            self.db_session.commit()
            logger.info(f"Microservice token metric with ID {token_metrics_id} deleted successfully.")
            return True
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error deleting microservice token metric with ID {token_metrics_id}: {e}")
            raise

    def get_token_metrics_by_microservice_id(self, microservice_id: int) -> List[MicroserviceLLMMetrics]:
        """
        Retrieves all microservice token metrics for a specific microservice.
        """
        logger.info(f"Retrieving microservice token metrics for microservice ID: {microservice_id}")
        try:
            token_metrics = self.db_session.query(MicroserviceLLMMetrics).filter(
                MicroserviceLLMMetrics.microservice_id == microservice_id
            ).all()
            logger.info(f"Retrieved {len(token_metrics)} token metrics for microservice ID {microservice_id}.")
            return token_metrics
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving token metrics for microservice ID {microservice_id}: {e}")
            raise
