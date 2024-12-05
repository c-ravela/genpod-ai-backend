from typing import List, Optional

from apis.microservice.service import MicroserviceService
from database.entities.microservices import Microservice
from utils.logs.logging_utils import logger


class MicroserviceController:
    """
    Controller class for handling Microservice-related operations.
    """

    def __init__(self):
        logger.debug("Initializing MicroserviceController.")
        self.microservice_service = MicroserviceService()
        logger.info("MicroserviceController initialized successfully.")

    def create(self, microservice: Microservice) -> None:
        """
        Creates a new microservice.
        """
        logger.info(f"Creating a new microservice: {microservice}")
        try:
            self.microservice_service.create_microservice(microservice)
            logger.info(f"Microservice created successfully: {microservice}")
        except Exception as e:
            logger.error(f"Failed to create microservice: {e}")
            raise

    def update(self, microservice: Microservice) -> Optional[Microservice]:
        """
        Updates an existing microservice.
        """
        logger.info(f"Updating microservice: {microservice}")
        try:
            updated_microservice = self.microservice_service.update_microservice(microservice)
            if updated_microservice:
                logger.info(f"Microservice updated successfully: {updated_microservice}")
            else:
                logger.warning(f"Microservice update returned None: {microservice}")
            return updated_microservice
        except Exception as e:
            logger.error(f"Failed to update microservice: {e}")
            raise

    def delete(self, microservice_id: int) -> bool:
        """
        Deletes a microservice.
        """
        logger.info(f"Deleting microservice with ID: {microservice_id}")
        try:
            result = self.microservice_service.delete_microservice(microservice_id)
            if result:
                logger.info(f"Microservice with ID {microservice_id} deleted successfully.")
            else:
                logger.warning(f"Microservice with ID {microservice_id} could not be deleted.")
            return result
        except Exception as e:
            logger.error(f"Failed to delete microservice with ID {microservice_id}: {e}")
            raise

    def get_microservice(self, microservice_id: int) -> Optional[Microservice]:
        """
        Retrieves a single microservice by ID.
        """
        logger.info(f"Retrieving microservice with ID: {microservice_id}")
        try:
            microservice = self.microservice_service.get_microservice_by_id(microservice_id)
            if microservice:
                logger.info(f"Microservice retrieved successfully: {microservice}")
            else:
                logger.warning(f"No microservice found with ID: {microservice_id}")
            return microservice
        except Exception as e:
            logger.error(f"Failed to retrieve microservice with ID {microservice_id}: {e}")
            raise
    
    def get_microservices(self, user_id: int) -> List[Microservice]:
        """
        Retrieves all microservices for a specific user.
        """
        logger.info(f"Retrieving all microservices for user ID: {user_id}")
        try:
            microservices = self.microservice_service.get_microservices(user_id)
            logger.info(f"Retrieved {len(microservices)} microservices for user ID: {user_id}")
            return microservices
        except Exception as e:
            logger.error(f"Failed to retrieve microservices for user ID {user_id}: {e}")
            raise

    def get_microservices_by_project_id(self, user_id: int, project_id: int) -> List[Microservice]:
        """
        Retrieves all microservices for a specific user and project.
        """
        logger.info(f"Retrieving microservices for user ID: {user_id}, project ID: {project_id}")
        try:
            microservices = self.microservice_service.get_microservices(user_id, project_id)
            logger.info(f"Retrieved {len(microservices)} microservices for user ID {user_id}, project ID {project_id}")
            return microservices
        except Exception as e:
            logger.error(f"Failed to retrieve microservices for user ID {user_id}, project ID {project_id}: {e}")
            raise
