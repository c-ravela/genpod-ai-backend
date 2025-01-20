import os
from datetime import datetime

from typing import List, Dict
import json
from enum import Enum
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

def serialize_for_json(data):
    """
    Recursively converts Enums, Pydantic BaseModel objects, and other non-serializable
    data types to JSON-serializable types.
    
    Args:
        data: The data structure to serialize.
        
    Returns:
        A data structure ready for JSON serialization, with Enums, BaseModel objects,
        and other non-serializable objects converted to JSON-compatible types.
    """
    if isinstance(data, Enum):
        return data.value  # Convert Enum to its value (string or int)
    elif isinstance(data, BaseModel):
        # Convert BaseModel instance to dictionary and process fields recursively
        return {key: serialize_for_json(value) for key, value in data.model_dump().items()}
    elif isinstance(data, dict):
        # Recursively process each dictionary key-value pair
        return {key: serialize_for_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        # Recursively process each item in the list
        return [serialize_for_json(item) for item in data]
    elif isinstance(data, tuple):
        # Convert tuples to lists and process each item recursively
        return [serialize_for_json(item) for item in data]
    return data  # Return data if it's already JSON-serializable

def write_supervisor_state_to_file(supervisor_response: List[Dict[str, Dict]], filename: str = "/home/cravela/Desktop/supervisor_state.json"):
    """
    Writes the supervisor state to a file every 3 seconds, overwriting the file content each time.
    
    Args:
        supervisor_response (List[Dict[str, Dict]]): A list of dictionaries containing
                                                    each node's project state.
        filename (str): Name of the file to write the state to.
    """

    with open(filename, "w") as file:
        # Convert the supervisor response to a JSON-serializable structure
        serializable_response = serialize_for_json(supervisor_response)
        json.dump(serializable_response, file, indent=4)
