from abc import ABC

from sqlalchemy import MetaData, create_engine
from sqlalchemy.exc import SQLAlchemyError
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
            logger.debug("No existing Database instance found. Creating a new one.")
            Database._instance = super().__new__(cls)
            logger.debug("Database instance object created.")
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
            logger.debug(f"Database URI: {db_uri}")
            self._engine = create_engine(
                db_uri,
                connect_args={"check_same_thread": False}
            )
            logger.debug("SQLAlchemy engine created successfully.")
            self._session_factory = sessionmaker(
                bind=self._engine, autoflush=False, autocommit=False
            )
            logger.debug("Session factory created successfully.")
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
            logger.info("Starting process to create missing tables.")
            logger.debug("Reflecting existing database schema...")
            metadata = MetaData()
            metadata.reflect(bind=self._engine)
            logger.debug("Database schema reflection completed.")

            logger.info("Checking for missing tables...")
            existing_tables = set(metadata.tables.keys())
            model_tables = set(Base.metadata.tables.keys())
            
            logger.debug(f"Existing tables in the database: {existing_tables}")
            logger.debug(f"Defined tables in the model: {model_tables}")
            
            missing_tables = model_tables - existing_tables
            if missing_tables:
                logger.info(f"Missing tables detected: {missing_tables}")
                for table_name in missing_tables:
                    logger.info(f"Creating table: {table_name}")
                    Base.metadata.tables[table_name].create(bind=self._engine)
                    logger.debug(f"Table {table_name} created successfully.")
                logger.info("All missing tables created successfully.")
            else:
                logger.info("No missing tables. Database schema is up-to-date.")
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error occurred while creating tables: {e}")
            raise
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
