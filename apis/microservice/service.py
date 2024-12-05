from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

from database.database import Database
from database.entities.microservices import Microservice
from utils.logs.logging_utils import logger


class MicroserviceService:
    """
    Service class for managing Microservice operations.
    """

    def __init__(self):
        logger.debug("Initializing MicroserviceService.")
        try:
            self.db_session = Database.get_db_session()
            logger.info("MicroserviceService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MicroserviceService: {e}")
            raise

    def create_microservice(self, microservice: Microservice) -> None:
        """
        Creates a new microservice record in the database.
        """
        logger.info(f"Creating microservice: {microservice}")
        try:
            self.db_session.add(microservice)
            self.db_session.commit()
            logger.info(f"Microservice created successfully: {microservice}")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error creating microservice: {e}")
            raise
    
    def get_microservice_by_id(self, microservice_id: int) -> Optional[Microservice]:
        """
        Retrieves a microservice by its ID.
        """
        logger.info(f"Retrieving microservice with ID: {microservice_id}")
        try:
            microservice = self.db_session.query(Microservice).filter(Microservice.id == microservice_id).first()
            if microservice:
                logger.info(f"Microservice retrieved successfully: {microservice}")
            else:
                logger.warning(f"No microservice found with ID: {microservice_id}")
            return microservice
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving microservice with ID {microservice_id}: {e}")
            raise

    def update_microservice(self, updated_microservice: Microservice) -> Optional[Microservice]:
        """
        Updates an existing microservice record using a Microservice object.
        """
        logger.info(f"Updating microservice with ID: {updated_microservice.id}")
        try:
            existing_microservice = self.get_microservice_by_id(updated_microservice.id)
            if not existing_microservice:
                logger.warning(f"No microservice found with ID: {updated_microservice.id} to update.")
                return None

            updateable_fields = {
                'microservice_name',
                'microservice_description',
                'status',
                'updated_by',
            }

            for field in updateable_fields:
                new_value = getattr(updated_microservice, field, None)
                if new_value is not None:
                    setattr(existing_microservice, field, new_value)

            self.db_session.commit()
            self.db_session.refresh(existing_microservice)
            logger.info(f"Microservice updated successfully: {existing_microservice}")
            return existing_microservice
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error updating microservice with ID {updated_microservice.id}: {e}")
            raise
    
    def delete_microservice(self, microservice_id: int) -> bool:
        """
        Soft deletes a microservice by setting the is_deleted flag.
        """
        logger.info(f"Deleting microservice with ID: {microservice_id}")
        try:
            microservice = self.get_microservice_by_id(microservice_id)
            if not microservice:
                logger.warning(f"No microservice found with ID: {microservice_id} to delete.")
                return False

            self.db_session.delete(microservice)
            self.db_session.commit()
            logger.info(f"Microservice with ID {microservice_id} deleted successfully.")
            return True
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error deleting microservice with ID {microservice_id}: {e}")
            raise

    def get_microservices(self, user_id: int) -> List[Microservice]:
        """
        Retrieves all microservices created by a specific user.
        """
        logger.info(f"Retrieving microservices for user ID: {user_id}")
        try:
            microservices = self.db_session.query(Microservice).filter(
                Microservice.created_by == user_id
            ).all()
            logger.info(f"Retrieved {len(microservices)} microservices for user ID {user_id}.")
            return microservices
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving microservices for user ID {user_id}: {e}")
            raise

    def get_microservices_by_project_id(self, user_id: int, project_id: int) -> List[Microservice]:
        """
        Retrieves all microservices for a specific user and project.
        """
        logger.info(f"Retrieving microservices for user ID: {user_id}, project ID: {project_id}")
        try:
            microservices = self.db_session.query(Microservice).filter(
                Microservice.created_by == user_id,
                Microservice.project_id == project_id,
            ).all()
            logger.info(f"Retrieved {len(microservices)} microservices for user ID {user_id}, project ID {project_id}.")
            return microservices
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving microservices for user ID {user_id}, project ID {project_id}: {e}")
            raise
