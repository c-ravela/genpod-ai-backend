"""
This module manages the Project generation path.
"""
from datetime import datetime

import os

project_path = os.getenv("PROJECT_PATH", os.path.join(os.getcwd(), "output", "project"))

def create_path_with_timestamp() -> str:
    """
    Creates a new directory with the current timestamp appended to the project path.
    The directory is created only if it does not already exist.

    Returns:
        str: The path to the newly created directory.
    """
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    project_path_timestamp = os.path.join(project_path, timestamp)
    if not os.path.exists(project_path_timestamp):
        os.makedirs(project_path_timestamp)

    return project_path_timestamp

"""
Define the path to the project creation
Example of how path looks

/opt/output/2024-06-27 22:22:43.027072
"""
GENERATED_PROJECT_PATH = create_path_with_timestamp()