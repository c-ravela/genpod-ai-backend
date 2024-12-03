import sqlite3

from database.tables.microservices import Microservices
from database.tables.projects import Projects
from database.tables.sessions import Sessions
from utils.logs.logging_utils import logger


class Database():
    """
    A singleton SQLite database wrapper.

    Args:
        db_path (str): Path to the SQLite database file.
    """

    _instance = None

    db_path: str

    connection: sqlite3.Connection
    cursor: sqlite3.Cursor

    # tables
    projects_table: Projects
    microservices_table: Microservices
    sessions_table: Sessions

    def __new__(cls, db_path=None):
        """
        Overrides the default __new__ method to ensure only one instance exists.
        """
        if cls._instance is None:
            logger.info("Creating a new Database instance.")
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialized = False  # Track if __init__ has been called
        return cls._instance
    
    def __init__(self, db_path):
        """
        Initializes the Database object. This will only execute once for the singleton instance.
        
        Args:
            db_path (str): Path to the SQLite database file.
        """
        if not self._initialized:  # Prevent re-initializing the singleton instance
            if not db_path:
                raise ValueError("A valid db_path must be provided during the first initialization.")
            
            self.db_path = db_path
            self.connection = self.__connect()
            self.cursor = self.connection.cursor()

            # Initialize table instances
            self.projects_table = Projects(self.connection)
            self.microservices_table = Microservices(self.connection)
            self.sessions_table = Sessions(self.connection)

            self._initialized = True  # Mark as initialized
            logger.info("Database instance initialized.")
    
    @classmethod
    def get_instance(cls):
        """
        Provides access to the singleton instance. 
        Ensures the instance is already initialized.

        Returns:
            Database: The singleton Database instance.

        Raises:
            ValueError: If the instance has not been initialized.
        """
        if cls._instance is None or not cls._instance._initialized:
            raise ValueError("Database instance is not initialized. Please initialize it with a valid db_path.")
        return cls._instance
    
    def __connect(self) -> sqlite3.Connection:
        """
        Establishes a connection to the SQLite database.

        Returns:
            sqlite3.Connection: A connection to the database.
        """
        try:
            logger.info("Connecting to the database at path: `%s`", self.db_path)
            sqCon = sqlite3.connect(self.db_path)
            logger.info("Database connection successful.")
            return sqCon
        except sqlite3.Error as sqe:
            logger.error("Error occurred while connecting to SQLite with db `%s`: %s", self.db_path, sqe)
            raise

    def setup_db(self):
        """Creates necessary tables in the database."""

        logger.info("Creating database tables...")
        try:
            # Create projects table
            self.projects_table.create()

            # Create microservice table
            self.microservices_table.create()

            # Create sessions table
            self.sessions_table.create()

            self.connection.commit()
        except sqlite3.Error as sqe:
            logger.error("Error Occurred while creating tables: %s", sqe)
            raise

    def close(self):
        """Closes the database connection."""

        self.connection.close()
        self.cursor.close()
        logger.info("Database connection closed")
