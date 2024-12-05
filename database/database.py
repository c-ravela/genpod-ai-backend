from abc import ABC

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from database.database_base import Base
from utils.logs.logging_utils import logger


class Database(ABC):
    """
    Abstract base class for managing database connections using SQLAlchemy.
    """
    
    _instance = None

    def __new__(cls, db_uri: str):
        """
        Ensures only one instance of the class exists.
        """
        if Database._instance is None:
            Database._instance = super().__new__(cls)
            logger.debug("Creating a new Database instance.")
            try:
                Database._instance._initialize(db_uri)
                logger.info("Singleton Database instance created!")
            except Exception as e:
                logger.error(f"Error initializing the Database instance: {e}")
                raise
        
        logger.debug("Returning existing Database instance.")
        return Database._instance
    
    def _initialize(self, db_uri: str):
        """
        Initialize the database connection.
        """
        try:
            logger.info("Initializing database connection.")
            self._engine = create_engine(
                db_uri,
                connect_args={"check_same_thread": False},
                # echo=True
            )
            self._session_factory = sessionmaker(
                bind=self._engine, autoflush=False, autocommit=False
            )
            self._session = self._session_factory()
            logger.info("Database connection and session factory set up successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize the database connection: {e}")
            raise

    def create_tables(self):
        """
        Creates tables based on SQLAlchemy models if they don't already exist.
        """
        try:
            logger.info("Creating tables based on SQLAlchemy models.")
            import database.entities
            Base.metadata.create_all(bind=self._engine)
            logger.info("Tables created successfully.")
        except Exception as e:
            logger.error(f"Error occurred while creating tables: {e}")
            raise

    @classmethod
    def get_db_session(cls) -> Session:
        """
        Provides access to the singleton database session.

        Returns:
            Session: The SQLAlchemy session instance.

        Raises:
            Exception: If the database instance is not initialized.
        """
        if Database._instance is None:
            logger.error("Attempted to access the database session without initializing the instance.")
            raise Exception("Database instance is not initialized.")
        logger.debug("Providing the database session.")
        return Database._instance._session

    @classmethod
    def close_session(cls):
        """
        Closes the singleton session.
        """
        if cls._instance and cls._instance._session:
            try:
                logger.info("Closing the database session.")
                cls._instance._session.close()
                logger.debug("Database session closed successfully.")
            except Exception as e:
                logger.error(f"Error occurred while closing the session: {e}")
        else:
            logger.warning("No active session to close.")
    
    @classmethod
    def dispose_engine(cls):
        """
        Disposes of the engine and session factory.
        """
        if cls._instance and cls._instance._engine:
            try:
                logger.info("Disposing of the database engine and session factory.")
                cls._instance._engine.dispose()
                logger.debug("Database engine disposed successfully.")
            except Exception as e:
                logger.error(f"Error occurred while disposing the engine: {e}")
        else:
            logger.warning("No active engine to dispose.")
