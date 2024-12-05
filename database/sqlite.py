from database.database import Database
from utils.logs.logging_utils import logger


class SQLite(Database):
    """
    SQLite-specific implementation of the Database class.
    """

    def __new__(cls, db_path: str):
        """
        Constructs the db_uri and initializes the SQLite database connection.

        Args:
            db_path (str): Path to the SQLite database file.
        """
        if not db_path:
            logger.error("Database path not provided. A valid path is required for SQLite.")
            raise ValueError("A valid database path must be provided for SQLite.")
        
        db_uri = f"sqlite:///{db_path}"
        logger.info(f"Constructed SQLite database URI: {db_uri}")
        
        try:
            instance = super().__new__(cls, db_uri)
            logger.info("SQLite Database instance created successfully.")
            return instance
        except Exception as e:
            logger.error(f"Error initializing SQLite Database instance: {e}")
            raise
