import sqlite3
from datetime import datetime
from typing import Any, Dict

from database.tables.table import Table
from utils.logs.logging_utils import logger


class Sessions(Table):
    """
    Represents a database table for sessions.

    Args:
        connection (sqlite3.Connection): Connection to the SQLite database.
    """
    id: int
    project_id: int
    microservice_id: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    def __init__(self, connection: sqlite3.Connection):
        """
        Initializes the Sessions table object.
        
        Args:
            connection (sqlite3.Connection): Connection to the SQLite database.
        """
        self.name = "sessions"
        super().__init__(connection)

    def create(self) -> None:
        """
        Creates the mircoservices table in the database.
        """

        logger.info(f"Creating {self.name} Table...")

        create_table_query = f'''
        CREATE TABLE IF NOT EXISTS {self.name} (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL,
            microservice_id INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            created_by TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            FOREIGN KEY(microservice_id) REFERENCES microservices(id)
        );
        '''

        try:
            cursor = self.connection.cursor()

            cursor.execute(create_table_query)
            logger.info(f"{self.name} table created successfully.")

            self.connection.commit()
        except sqlite3.Error as sqe:
            logger.error(f"Error creating {self.name} table: {sqe}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def insert(self, project_id: str, microservice_id: str, user_id: str) -> Dict[str, Any]:
        """
        Inserts a new session record into the table and returns it as a dictionary.
        """

        return super().insert(
            project_id=project_id,
            microservice_id=microservice_id,
            created_by=user_id,
            updated_by=user_id
        )
        
    def __valid_columns__(self) -> set:
        """
        Returns the set of valid columns for the sessions table.
        """
        return {"id", "project_id", "microservice_id", "created_at", "updated_at", "created_by", "updated_by"}