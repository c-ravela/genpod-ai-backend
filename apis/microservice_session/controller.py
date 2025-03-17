from typing import List

from apis.microservice_session.service import MicroserviceSessionService
from database.entities.microservice_sessions import MicroserviceSession
from utils.logs.logging_utils import logger


class MicroserviceSessionController:
    """
    Controller class for handling MicroserviceSession-related operations.
    """

    def __init__(self):
        logger.debug("Initializing MicroserviceSessionController.")
        self.session_service = MicroserviceSessionService()
        logger.info("MicroserviceSessionController initialized successfully.")

    def create(self, session: MicroserviceSession) -> None:
        """
        Creates a new microservice session.
        """
        logger.info(f"Creating a new microservice session: {session}")
        try:
            self.session_service.create_session(session)
            logger.info(f"Microservice session created successfully: {session}")
        except Exception as e:
            logger.error(f"Failed to create microservice session: {e}")
            raise

    def get_sessions(self, project_id: int, microservice_id: int, user_id: int) -> List[MicroserviceSession]:
        """
        Retrieves sessions based on project ID, microservice ID, and user ID.
        """
        logger.info(f"Retrieving sessions for project ID: {project_id}, microservice ID: {microservice_id}, user ID: {user_id}")
        try:
            sessions = self.session_service.get_sessions(project_id, microservice_id, user_id)
            logger.info(f"Retrieved {len(sessions)} sessions for project ID: {project_id}, microservice ID: {microservice_id}, user ID: {user_id}")
            return sessions
        except Exception as e:
            logger.error(f"Failed to retrieve sessions for project ID: {project_id}, microservice ID: {microservice_id}, user ID: {user_id}: {e}")
            raise
