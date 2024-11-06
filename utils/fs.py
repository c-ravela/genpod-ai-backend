import json
import os
from datetime import datetime
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel


def create_directory_with_timestamp(parent_directory: str) -> str:
    """
    This function creates a new directory within the specified parent directory. 
    The new directory's name is the current timestamp. If a directory with the 
    same timestamp already exists, no new directory is created.

    Args:
        parent_directory (str): The path of the parent directory where the new 
                                directory will be created.

    Returns:
        str: The path of the newly created directory. If a directory with the 
             same timestamp already exists, the path of the existing directory 
             is returned.
    """
    
    current_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    new_directory_path = os.path.join(parent_directory, current_timestamp)

    if not os.path.exists(new_directory_path):
        os.makedirs(new_directory_path)

    return new_directory_path

def read_file(path: str) -> str:
    """
    Reads the entire content of a text file at the specified path and returns it as a string.

    Parameters:
    path (str): The path to the text file to be read.

    Returns:
    str: The content of the file as a single string.
    """

    with open(path, 'r') as file:
        return file.read()
