from typing import List, Optional

from apis.application.service import ApplicationService
from database.entities.applications import Application
from utils.logger import logger


class ApplicationController:
    """
    Controller class for handling Application-related operations.
    """

    def __init__(self):
        logger.debug("Initializing ApplicationController.")
        self.application_service = ApplicationService()
        logger.info("ApplicationController initialized successfully.")

    def create(self, application: Application) -> None:
        """
        Creates a new application.
        """
        logger.info(f"Creating a new application: {application}")
        try:
            self.application_service.create_application(application)
            logger.info(f"Application created successfully: {application}")
        except Exception as e:
            logger.error(f"Failed to create application: {e}")
            raise

    def update(self, application: Application) -> Optional[Application]:
        """
        Updates an existing application.
        """
        logger.info(f"Updating application: {application}")
        try:
            updated_application = self.application_service.update_application(application)
            if updated_application:
                logger.info(f"Application updated successfully: {updated_application}")
            else:
                logger.warning(f"Application update returned None: {application}")
            return updated_application
        except Exception as e:
            logger.error(f"Failed to update application: {e}")
            raise

    def delete(self, application_id: int) -> bool:
        """
        Deletes a application.
        """
        logger.info(f"Deleting application with ID: {application_id}")
        try:
            result = self.application_service.delete_application(application_id)
            if result:
                logger.info(f"Application with ID {application_id} deleted successfully.")
            else:
                logger.warning(f"Application with ID {application_id} could not be deleted.")
            return result
        except Exception as e:
            logger.error(f"Failed to delete application with ID {application_id}: {e}")
            raise

    def get_application(self, application_id: int) -> Optional[Application]:
        """
        Retrieves a single application by ID.
        """
        logger.info(f"Retrieving application with ID: {application_id}")
        try:
            application = self.application_service.get_application_by_id(application_id)
            if application:
                logger.info(f"Application retrieved successfully: {application}")
            else:
                logger.warning(f"No application found with ID: {application_id}")
            return application
        except Exception as e:
            logger.error(f"Failed to retrieve application with ID {application_id}: {e}")
            raise
    
    def get_applications(self, user_id: int) -> List[Application]:
        """
        Retrieves all applications for a specific user.
        """
        logger.info(f"Retrieving all applications for user ID: {user_id}")
        try:
            applications = self.application_service.get_applications(user_id)
            logger.info(f"Retrieved {len(applications)} applications for user ID: {user_id}")
            return applications
        except Exception as e:
            logger.error(f"Failed to retrieve applications for user ID {user_id}: {e}")
            raise

    def get_applications_by_project_id(self, user_id: int, project_id: int) -> List[Application]:
        """
        Retrieves all applications for a specific user and project.
        """
        logger.info(f"Retrieving applications for user ID: {user_id}, project ID: {project_id}")
        try:
            applications = self.application_service.get_applications_by_project_id(user_id, project_id)
            logger.info(f"Retrieved {len(applications)} applications for user ID {user_id}, project ID {project_id}")
            return applications
        except Exception as e:
            logger.error(f"Failed to retrieve applications for user ID {user_id}, project ID {project_id}: {e}")
            raise
