from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

from database.database import Database
from database.entities.applications import Application
from utils.logger import logger


class ApplicationService:
    """
    Service class for managing Application operations.
    """

    def __init__(self):
        logger.debug("Initializing ApplicationService.")
        try:
            self.db_session = Database.get_db_session()
            logger.info("ApplicationService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ApplicationService: {e}")
            raise

    def create_application(self, application: Application) -> None:
        """
        Creates a new application record in the database.
        """
        logger.info(f"Creating application: {application}")
        try:
            self.db_session.add(application)
            self.db_session.commit()
            logger.info(f"Application created successfully: {application}")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error creating application: {e}")
            raise
    
    def get_application_by_id(self, application_id: int) -> Optional[Application]:
        """
        Retrieves a application by its ID.
        """
        logger.info(f"Retrieving application with ID: {application_id}")
        try:
            application = self.db_session.query(Application).filter(Application.id == application_id).first()
            if application:
                logger.info(f"Application retrieved successfully: {application}")
            else:
                logger.warning(f"No application found with ID: {application_id}")
            return application
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving application with ID {application_id}: {e}")
            raise

    def update_application(self, updated_application: Application) -> Optional[Application]:
        """
        Updates an existing application record using a Application object.
        """
        logger.info(f"Updating application with ID: {updated_application.id}")
        try:
            existing_application = self.get_application_by_id(updated_application.id)
            if not existing_application:
                logger.warning(f"No application found with ID: {updated_application.id} to update.")
                return None

            updateable_fields = {
                'application_name',
                'application_description',
                'status',
                'updated_by',
            }

            for field in updateable_fields:
                new_value = getattr(updated_application, field, None)
                if new_value is not None:
                    setattr(existing_application, field, new_value)

            self.db_session.commit()
            self.db_session.refresh(existing_application)
            logger.info(f"Application updated successfully: {existing_application}")
            return existing_application
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error updating application with ID {updated_application.id}: {e}")
            raise
    
    def delete_application(self, application_id: int) -> bool:
        """
        Soft deletes a application by setting the is_deleted flag.
        """
        logger.info(f"Deleting application with ID: {application_id}")
        try:
            application = self.get_application_by_id(application_id)
            if not application:
                logger.warning(f"No application found with ID: {application_id} to delete.")
                return False

            self.db_session.delete(application)
            self.db_session.commit()
            logger.info(f"Application with ID {application_id} deleted successfully.")
            return True
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error deleting application with ID {application_id}: {e}")
            raise

    def get_applications(self, user_id: int) -> List[Application]:
        """
        Retrieves all applications created by a specific user.
        """
        logger.info(f"Retrieving applications for user ID: {user_id}")
        try:
            applications = self.db_session.query(Application).filter(
                Application.created_by == user_id
            ).all()
            logger.info(f"Retrieved {len(applications)} applications for user ID {user_id}.")
            return applications
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving applications for user ID {user_id}: {e}")
            raise

    def get_applications_by_project_id(self, user_id: int, project_id: int) -> List[Application]:
        """
        Retrieves all applications for a specific user and project.
        """
        logger.info(f"Retrieving applications for user ID: {user_id}, project ID: {project_id}")
        try:
            applications = self.db_session.query(Application).filter(
                Application.created_by == user_id,
                Application.project_id == project_id,
            ).all()
            logger.info(f"Retrieved {len(applications)} applications for user ID {user_id}, project ID {project_id}.")
            return applications
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving applications for user ID {user_id}, project ID {project_id}: {e}")
            raise
