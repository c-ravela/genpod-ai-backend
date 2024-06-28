"""
This module manages the persistence of data for a single agent using a 
SQLite database.

Database: genpod.db
"""

import os

db_dir = os.path.join(os.getcwd(), "output", "database")

if not os.path.exists(db_dir):
    os.makedirs(db_dir)

# Define the path to the database file
PERSISTANCE_DB_PATH = os.path.join(db_dir, "genpod.db")