from typing import List, Optional

from apis.microservice_llm_metrics.service import MicroserviceLLMMetricsService
from database.entities.microservice_llm_metrics import MicroserviceLLMMetrics
from utils.logs.logging_utils import logger


class MicroserviceLLMMetricsController:
    """
    Controller class for handling MicroserviceLLMMetrics-related operations.
    """

    def __init__(self):
        logger.debug("Initializing MicroserviceLLMMetricsController.")
        self.token_metrics_service = MicroserviceLLMMetricsService()
        logger.info("MicroserviceLLMMetricsController initialized successfully.")

    def create(self, token_metrics: MicroserviceLLMMetrics) -> None:
        """
        Creates a new microservice token metric.
        """
        logger.info(f"Creating a new microservice token metric: {token_metrics}")
        try:
            self.token_metrics_service.create_token_metrics(token_metrics)
            logger.info(f"Microservice token metric created successfully: {token_metrics}")
        except Exception as e:
            logger.error(f"Failed to create microservice token metric: {e}")
            raise

    def update(self, token_metrics: MicroserviceLLMMetrics) -> Optional[MicroserviceLLMMetrics]:
        """
        Updates an existing microservice token metric.
        """
        logger.info(f"Updating microservice token metric: {token_metrics}")
        try:
            updated_token_metrics = self.token_metrics_service.update_token_metrics(token_metrics)
            if updated_token_metrics:
                logger.info(f"Microservice token metric updated successfully: {updated_token_metrics}")
            else:
                logger.warning(f"Microservice token metric update returned None: {token_metrics}")
            return updated_token_metrics
        except Exception as e:
            logger.error(f"Failed to update microservice token metric: {e}")
            raise

    def delete(self, token_metrics_id: int) -> bool:
        """
        Deletes a microservice token metric.
        """
        logger.info(f"Deleting microservice token metric with ID: {token_metrics_id}")
        try:
            result = self.token_metrics_service.delete_token_metrics(token_metrics_id)
            if result:
                logger.info(f"Microservice token metric with ID {token_metrics_id} deleted successfully.")
            else:
                logger.warning(f"Microservice token metric with ID {token_metrics_id} could not be deleted.")
            return result
        except Exception as e:
            logger.error(f"Failed to delete microservice token metric with ID {token_metrics_id}: {e}")
            raise

    def get_token_metrics(self, token_metrics_id: int) -> Optional[MicroserviceLLMMetrics]:
        """
        Retrieves a single microservice token metric by ID.
        """
        logger.info(f"Retrieving microservice token metric with ID: {token_metrics_id}")
        try:
            token_metrics = self.token_metrics_service.get_token_metrics_by_id(token_metrics_id)
            if token_metrics:
                logger.info(f"Microservice token metric retrieved successfully: {token_metrics}")
            else:
                logger.warning(f"No microservice token metric found with ID: {token_metrics_id}")
            return token_metrics
        except Exception as e:
            logger.error(f"Failed to retrieve microservice token metric with ID {token_metrics_id}: {e}")
            raise
    
    def get_token_metrics_by_microservice(self, microservice_id: int) -> List[MicroserviceLLMMetrics]:
        """
        Retrieves all microservice token metrics for a specific microservice.
        """
        logger.info(f"Retrieving all microservice token metrics for microservice ID: {microservice_id}")
        try:
            token_metrics_list = self.token_metrics_service.get_token_metrics_by_microservice_id(microservice_id)
            logger.info(f"Retrieved {len(token_metrics_list)} token metrics for microservice ID: {microservice_id}")
            return token_metrics_list
        except Exception as e:
            logger.error(f"Failed to retrieve token metrics for microservice ID {microservice_id}: {e}")
            raise
