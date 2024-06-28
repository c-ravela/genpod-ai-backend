import os
import datetime

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
    
    current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    new_directory_path = os.path.join(parent_directory, current_timestamp)

    if not os.path.exists(new_directory_path):
        os.makedirs(new_directory_path)

    return new_directory_path
