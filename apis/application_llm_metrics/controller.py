from typing import List, Optional

from apis.application_llm_metrics.service import ApplicationLLMMetricsService
from database.entities.application_llm_metrics import ApplicationLLMMetrics
from utils.logger import logger


class ApplicationLLMMetricsController:
    """
    Controller class for handling ApplicationLLMMetrics-related operations.
    """

    def __init__(self):
        logger.debug("Initializing ApplicationLLMMetricsController.")
        self.token_metrics_service = ApplicationLLMMetricsService()
        logger.info("ApplicationLLMMetricsController initialized successfully.")

    def create(self, token_metrics: ApplicationLLMMetrics) -> None:
        """
        Creates a new application token metric.
        """
        logger.info(f"Creating a new application token metric: {token_metrics}")
        try:
            self.token_metrics_service.create_token_metrics(token_metrics)
            logger.info(f"Application token metric created successfully: {token_metrics}")
        except Exception as e:
            logger.error(f"Failed to create application token metric: {e}")
            raise

    def update(self, token_metrics: ApplicationLLMMetrics) -> Optional[ApplicationLLMMetrics]:
        """
        Updates an existing application token metric.
        """
        logger.info(f"Updating application token metric: {token_metrics}")
        try:
            updated_token_metrics = self.token_metrics_service.update_token_metrics(token_metrics)
            if updated_token_metrics:
                logger.info(f"Application token metric updated successfully: {updated_token_metrics}")
            else:
                logger.warning(f"Application token metric update returned None: {token_metrics}")
            return updated_token_metrics
        except Exception as e:
            logger.error(f"Failed to update application token metric: {e}")
            raise

    def delete(self, token_metrics_id: int) -> bool:
        """
        Deletes a application token metric.
        """
        logger.info(f"Deleting application token metric with ID: {token_metrics_id}")
        try:
            result = self.token_metrics_service.delete_token_metrics(token_metrics_id)
            if result:
                logger.info(f"Application token metric with ID {token_metrics_id} deleted successfully.")
            else:
                logger.warning(f"Application token metric with ID {token_metrics_id} could not be deleted.")
            return result
        except Exception as e:
            logger.error(f"Failed to delete application token metric with ID {token_metrics_id}: {e}")
            raise

    def get_token_metrics(self, token_metrics_id: int) -> Optional[ApplicationLLMMetrics]:
        """
        Retrieves a single application token metric by ID.
        """
        logger.info(f"Retrieving application token metric with ID: {token_metrics_id}")
        try:
            token_metrics = self.token_metrics_service.get_token_metrics_by_id(token_metrics_id)
            if token_metrics:
                logger.info(f"Application token metric retrieved successfully: {token_metrics}")
            else:
                logger.warning(f"No application token metric found with ID: {token_metrics_id}")
            return token_metrics
        except Exception as e:
            logger.error(f"Failed to retrieve application token metric with ID {token_metrics_id}: {e}")
            raise
    
    def get_token_metrics_by_application(self, application_id: int, project_id: int, user_id: int) -> List[ApplicationLLMMetrics]:
        """
        Retrieves all application token metrics for a specific application.
        """
        logger.info(f"Retrieving all application token metrics for application ID: {application_id}")
        try:
            token_metrics_list = self.token_metrics_service.get_token_metrics_by_application_id(application_id, project_id, user_id)
            logger.info(f"Retrieved {len(token_metrics_list)} token metrics for application ID: {application_id}")
            return token_metrics_list
        except Exception as e:
            logger.error(f"Failed to retrieve token metrics for application ID {application_id}: {e}")
            raise
