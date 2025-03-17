from typing import List

from sqlalchemy.exc import SQLAlchemyError

from database.database import Database
from database.entities.microservice_sessions import MicroserviceSession
from utils.logs.logging_utils import logger


class MicroserviceSessionService:
    """
    Service class for managing MicroserviceSession operations.
    """

    def __init__(self):
        logger.debug("Initializing MicroserviceSessionService.")
        try:
            self.db_session = Database.get_db_session()
            logger.info("MicroserviceSessionService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MicroserviceSessionService: {e}")
            raise

    def create_session(self, session: MicroserviceSession) -> MicroserviceSession:
        """
        Creates a new microservice session record in the database.
        """
        logger.info(f"Creating a new microservice session: {session}")
        try:
            self.db_session.add(session)
            self.db_session.commit()
            logger.info(f"Microservice session created successfully: {session}")
            return session
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Failed to create microservice session: {e}")
            raise

    def get_sessions(self, project_id: int, microservice_id: int, user_id: int) -> List[MicroserviceSession]:
        """
        Retrieves all microservice sessions for a specific project, microservice, and user.
        """
        logger.info(f"Retrieving sessions for project ID: {project_id}, microservice ID: {microservice_id}, user ID: {user_id}")
        try:
            sessions = self.db_session.query(MicroserviceSession).filter(
                MicroserviceSession.project_id == project_id,
                MicroserviceSession.microservice_id == microservice_id,
                MicroserviceSession.created_by == user_id
            ).all()
            logger.info(f"Retrieved {len(sessions)} sessions for project ID: {project_id}, microservice ID: {microservice_id}, user ID: {user_id}")
            return sessions
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve sessions for project ID: {project_id}, microservice ID: {microservice_id}, user ID: {user_id}: {e}")
            raise
