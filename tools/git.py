"""
This module provides a Git class with a method to create a new Git repository at a specified path.
"""
import os
import subprocess
from typing import Annotated

from langchain.tools import tool


class Git:
    """
    This class provides a method to create a new Git repository at a specified path.
    """
    
    @tool
    def create_git_repo(
        repo_path: Annotated[
            str,
            "The absolute path where the 'git init' command will be executed."
        ]
    ) -> tuple[bool, str]:
        """
        Creates a new Git repository at the specified absolute path.

        Args:
            repo_path (str): The absolute path where the 'git init' command will be executed.

        Returns:
            tuple: A tuple containing a boolean and a string. The boolean is True if an error 
            occurred, False otherwise. The string contains a success message with the path of 
            the newly created Git repository or an error message.
        """
        try:
            # Ensure the directory exists before initializing the Git repository
            os.makedirs(repo_path, exist_ok=True)
            
            subprocess.check_output(['git', 'init'], cwd=repo_path)
            
            return (False, f"Success! A new Git repository was created at the following location: '{repo_path}'")
        except Exception as e:
            return (True, f"An error occurred while attempting to create a new Git repository. Here's what went wrong: '{repr(e)}'")
