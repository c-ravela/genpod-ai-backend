from langchain.tools import tool

from typing import Annotated

import os
import subprocess

class Git:

    @tool
    def create_git_repo(
        project_name: Annotated[str, "Name of the new Git repository that should be created."],
        repo_path: Annotated[str,"Path where the repository is created."]
    ) -> tuple[bool, str]:
        """
        Creates a new Git repository at the specified path.

        Args:
            project_name (str): Name of the new Git repository that should be created.
            PROJECT_PATH (str): Path where the new Git repository will be created.

        Returns:
            A dictionary containing the path of the newly created Git repository or an error message.
        """
        try:
            repo_path = os.path.join(PROJECT_PATH, project_name)
            
            # Ensure the directory exists before initializing the Git repository
            os.makedirs(repo_path, exist_ok=True)
            
            subprocess.check_output(['git', 'init'], cwd=repo_path)
            
            return (False, f"Git repository created successfully: {repo_path}")
        except Exception as e:
            return (True, f"Failed to create a new Git repository. Error: {repr(e)}")
