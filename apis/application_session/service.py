from typing import List

from sqlalchemy.exc import SQLAlchemyError

from database.database import Database
from database.entities.application_sessions import ApplicationSession
from utils.logger import logger


class ApplicationSessionService:
    """
    Service class for managing ApplicationSession operations.
    """

    def __init__(self):
        logger.debug("Initializing ApplicationSessionService.")
        try:
            self.db_session = Database.get_db_session()
            logger.info("ApplicationSessionService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ApplicationSessionService: {e}")
            raise

    def create_session(self, session: ApplicationSession) -> ApplicationSession:
        """
        Creates a new application session record in the database.
        """
        logger.info(f"Creating a new application session: {session}")
        try:
            self.db_session.add(session)
            self.db_session.commit()
            logger.info(f"Application session created successfully: {session}")
            return session
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Failed to create application session: {e}")
            raise

    def get_sessions(self, project_id: int, application_id: int, user_id: int) -> List[ApplicationSession]:
        """
        Retrieves all application sessions for a specific project, application, and user.
        """
        logger.info(f"Retrieving sessions for project ID: {project_id}, application ID: {application_id}, user ID: {user_id}")
        try:
            sessions = self.db_session.query(ApplicationSession).filter(
                ApplicationSession.project_id == project_id,
                ApplicationSession.application_id == application_id,
                ApplicationSession.created_by == user_id
            ).all()
            logger.info(f"Retrieved {len(sessions)} sessions for project ID: {project_id}, application ID: {application_id}, user ID: {user_id}")
            return sessions
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve sessions for project ID: {project_id}, application ID: {application_id}, user ID: {user_id}: {e}")
            raise
