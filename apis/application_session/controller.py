from typing import List

from apis.application_session.service import ApplicationSessionService
from database.entities.application_sessions import ApplicationSession
from utils.logger import logger


class ApplicationSessionController:
    """
    Controller class for handling ApplicationSession-related operations.
    """

    def __init__(self):
        logger.debug("Initializing ApplicationSessionController.")
        self.session_service = ApplicationSessionService()
        logger.info("ApplicationSessionController initialized successfully.")

    def create(self, session: ApplicationSession) -> None:
        """
        Creates a new application session.
        """
        logger.info(f"Creating a new application session: {session}")
        try:
            self.session_service.create_session(session)
            logger.info(f"Application session created successfully: {session}")
        except Exception as e:
            logger.error(f"Failed to create application session: {e}")
            raise

    def get_sessions(self, project_id: int, application_id: int, user_id: int) -> List[ApplicationSession]:
        """
        Retrieves sessions based on project ID, application ID, and user ID.
        """
        logger.info(f"Retrieving sessions for project ID: {project_id}, application ID: {application_id}, user ID: {user_id}")
        try:
            sessions = self.session_service.get_sessions(project_id, application_id, user_id)
            logger.info(f"Retrieved {len(sessions)} sessions for project ID: {project_id}, application ID: {application_id}, user ID: {user_id}")
            return sessions
        except Exception as e:
            logger.error(f"Failed to retrieve sessions for project ID: {project_id}, application ID: {application_id}, user ID: {user_id}: {e}")
            raise
