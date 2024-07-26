"""
This module manages the persistence of data for a single agent using a 
SQLite database.
"""

import os

db_dir = os.path.join(os.getcwd(), "output", "databases")

def set_persistance_db(name:str="genpod", timestamp: str="") -> str:
    """
    This function set the path for db.

    timestamp: current_time
    name: name of the database without ".db"

    return: db path
    """

    db_dir_with_timestamp = os.path.join(db_dir, timestamp)
    if not os.path.exists(db_dir_with_timestamp):
        os.makedirs(db_dir_with_timestamp)

    return os.path.join(db_dir_with_timestamp, f"{name}.db")

PERSISTANCE_DB_PATH = os.path.join(db_dir, "genpod_test.db")