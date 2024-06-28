"""
This module is responsible for managing the path generation for projects. 
It provides functionalities to set up a unique project path by creating a new 
directory with a timestamp. This ensures that each project has its own 
dedicated directory, preventing any overlap or overwriting of data.

The main function in this module is `set_project_path`, which sets the path 
for a new project and creates a new directory at that path with the current 
timestamp.
"""

from utils.fs import create_directory_with_timestamp

import os

def set_project_path(project_path: str=os.path.join(os.getcwd(), "output", "project")) -> str:
    """
    Sets the path for a new project and creates a new directory at that path 
    with the current timestamp. If the path already exists, no new directory 
    is created.

    Args:
        project_path (str, optional): The base path where the new project 
                                       directory will be created. Defaults to 
                                       the 'output/project' directory in the 
                                       current working directory.

    Returns:
        str: The path of the newly created project directory. If a directory 
             with the same timestamp already exists, the path of the existing 
             directory is returned.

    Example:
        If the function is called on June 27, 2024 at 22:22:43.027072, the 
        returned path will be '<cwd>/output/project/2024-06-27 22:22:43.027072'.

    """

    return create_directory_with_timestamp(project_path)
