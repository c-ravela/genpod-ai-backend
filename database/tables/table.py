import sqlite3
from datetime import datetime
from typing import Any, Dict

from utils.logs.logging_utils import logger


class Table:
    """
    A base class for managing a SQLite database table.
    """
    name: str
    curr_id: int

    connection: sqlite3.Connection

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.curr_id = None

    def create(self) -> None:
        """
        Creates the table in the database. Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement the create method")

    def insert(self, **columns) -> Dict[str, Any]:
        """
        Inserts a new record into the table and returns the record as a dictionary.
        """
        logger.info(f"Inserting a record into {self.name}...")

        if self.curr_id is None:
            self.curr_id = self._max_id()
        
        self.curr_id += 1
        columns['id'] = self.curr_id
        columns['created_at'] = datetime.now()
        columns['updated_at'] = datetime.now()

        column_names = ', '.join(columns.keys())
        placeholders = ', '.join('?' * len(columns))
        insert_query = f'''
        INSERT INTO {self.name} ({column_names})
        VALUES ({placeholders});
        '''

        try:
            cursor = self.connection.cursor()
            cursor.execute(insert_query, tuple(columns.values()))
            logger.info(f"A record inserted into {self.name} table.")
            self.connection.commit()
        except sqlite3.Error as sqe:
            logger.error(f"Error inserting into {self.name} table: {sqe}")
            raise
        finally:
            if cursor:
                cursor.close()

        # Return the inserted record
        return self.select(self.curr_id)
    
    def update(self, record_id: int, **columns) -> Dict[str, Any]:
        """
        Updates a record in the table based on the provided ID and columns, and returns the updated record as a dictionary.
        """
        VALID_COLUMNS = self.__valid_columns__()

        if not VALID_COLUMNS:
            raise NotImplementedError("Subclasses must define VALID_COLUMNS")

        invalid_columns = set(columns.keys()) - VALID_COLUMNS
        if invalid_columns:
            raise ValueError(f"Invalid column names: {', '.join(invalid_columns)} for table '{self.name}' update.")
        
        update_query = f'''
        UPDATE {self.name} 
        SET {', '.join(f"{col} = ?" for col in columns)}
        WHERE id = ?;
        '''

        try:
            cursor = self.connection.cursor()
            cursor.execute(update_query, (*columns.values(), record_id))
            logger.info(f"Updated {cursor.rowcount} record(s) in the '{self.name}' table.")
            self.connection.commit()
        except sqlite3.Error as sqe:
            logger.error(f"Error updating {self.name} table: {sqe}")
            raise
        finally:
            if cursor:
                cursor.close()

        # Return the updated record
        return self.select(record_id)

    def select(self, record_id: int) -> Dict[str, Any]:
        """
        Selects a record by ID and returns it as a dictionary.
        """
        query = f"SELECT * FROM {self.name} WHERE id = ?"
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (record_id,))
            row = cursor.fetchone()
            if row:
                record = {column[0]: row[i] for i, column in enumerate(cursor.description)}
                return record
            else:
                return {}
        except sqlite3.Error as sqe:
            logger.error(f"Error retrieving record {record_id} from {self.name} table: {sqe}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def delete(self, record_id: int) -> None:
        """
        Deletes a record by ID.
        """
        query = f"DELETE FROM {self.name} WHERE id = ?"
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (record_id,))
            logger.info(f"Deleted record {record_id} from {self.name} table.")
            self.connection.commit()
        except sqlite3.Error as sqe:
            logger.error(f"Error deleting record {record_id} from {self.name} table: {sqe}")
            raise
        finally:
            if cursor:
                cursor.close()

    def _update_instance_from_db(self, record_id: int) -> None:
        """
        Fetch the record with the given ID from the database and update the instance attributes.
        """
        query = f"SELECT * FROM {self.name} WHERE id = ?"
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, (record_id,))
            row = cursor.fetchone()
            if row:
                for i, column in enumerate(cursor.description):
                    setattr(self, column[0], row[i])
        except sqlite3.Error as sqe:
            logger.error(f"Error retrieving record {record_id} from {self.name} table: {sqe}")
            raise
        finally:
            if cursor:
                cursor.close()
                
    def _max_id(self) -> int:
        """
        Retrieves the maximum ID from the table.
        """
        query = f'''
        SELECT id FROM {self.name}
        ORDER BY id DESC
        LIMIT 1;
        '''
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else 0
        except sqlite3.Error as sqe:
            logger.error(f"Error getting max row id: {sqe}")
            raise
        finally:
            if cursor:
                cursor.close()

    def __valid_columns__(self) -> set:
        """
        Returns a set of valid columns for the table. Must be implemented in subclasses.
        """
        raise NotImplementedError("Subclasses must define valid columns")
