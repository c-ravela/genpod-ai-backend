import os
from typing import Any, Dict

import yaml


class InvalidFilePathError(Exception):
    """Custom exception for invalid file paths."""
    pass

def read_yaml(file_path: str) -> Dict[str, Any]:
    """
    Reads a YAML file and returns its content as a dictionary.

    Parameters:
    - file_path (str): The full path of the YAML file to be read.

    Returns:
    - dict: The parsed contents of the YAML file.

    Raises:
    - FileNotFoundError: If the file does not exist at the provided path.
    - InvalidFilePathError: If the file does not have a valid .yaml or .yml extension.
    - yaml.YAMLError: If there is an error in parsing the YAML file.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")
    
    if not (file_path.endswith('.yaml') or file_path.endswith('.yml')):
        raise InvalidFilePathError(f"Invalid file extension for {file_path}. Expected a .yaml or .yml file.")
    
    try:
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as ye:
        raise yaml.YAMLError(f"Error parsing YAML file {file_path}: {ye}")
