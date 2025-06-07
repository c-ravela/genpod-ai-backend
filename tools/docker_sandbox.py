"""
Module: docker_sandbox_executor_tool.py

This module provides the docker_sandbox_executor tool function, which executes code in a Docker sandbox environment
using a provided Dockerfile and source code file. It supports optional volume mounts, where the 'mounts' parameter
should be a dictionary mapping container target paths to absolute host paths.
For example: {"/app": "/home/user/myproject"}.
"""

import os
from typing import Dict, List, Optional

from docker.types import Mount
from langchain.tools import tool
from llm_sandbox import SandboxSession, SupportedLanguage

docker_sandbox_description=("Execute code in a Docker sandbox environment using a provided Dockerfile and source code file. "
"Arguments must be absolute paths. Supported languages: python, java, javascript, cpp, go, ruby, csharp. "
"The Dockerfile is assumed to handle copying the source code into the image. "
"Provide a command to execute inside the container. Optionally, specify volume mounts for shared volumes. "
"The 'mounts' parameter should be a dictionary where keys are container target paths and values are "
"the corresponding absolute host paths to mount. For example: {\"/app\": \"/home/user/myproject\"}.")
# @tool("docker_sandbox_executor")
def docker_sandbox_executor(
    dockerfile: str,
    source_path: str,
    language: str,
    command: str,
    libraries: Optional[List[str]] = None,
    mounts: Optional[Dict[str, str]] = None
) -> str:
    """
    Execute code in a Docker sandbox using a Dockerfile and a source code file, with optional volume mounts.

    Args:
        dockerfile (str): Absolute path to the Dockerfile.
        source_path (str): Absolute path to the source code file.
        language (str): Programming language (e.g., "python", "cpp", "csharp", etc.).
        command (str): The command to execute inside the container.
        libraries (Optional[List[str]]): Optional list of libraries to install prior to execution.
        mounts (Optional[Dict[str, str]]): Optional dictionary for volume mounting between host and container.
            - **Key:** The target path inside the container where the volume should be mounted.
            - **Value:** The corresponding absolute host path that will be mounted.
            
            Example: {"/app": "/home/user/myproject"} means the host directory 
            "/home/user/myproject" will be mounted at "/app" inside the container.
    
    Returns:
        str: The output from the sandbox execution.
    
    Raises:
        ValueError: If provided paths (dockerfile, source_path, or host paths in mounts) are not absolute.
        ValueError: If an unsupported language is provided.
    """
    # Validate that the provided paths are absolute.
    if not os.path.isabs(dockerfile):
        raise ValueError("The dockerfile path must be an absolute path.")
    if not os.path.isabs(source_path):
        raise ValueError("The source code path must be an absolute path.")

    # Supported languages defined in the Sandbox package.
    supported_languages = [
        SupportedLanguage.PYTHON,
        SupportedLanguage.JAVA,
        SupportedLanguage.JAVASCRIPT,
        SupportedLanguage.CPP,
        SupportedLanguage.GO,
        SupportedLanguage.RUBY,
        SupportedLanguage.CSHARP
    ]
    if language.lower() not in [str(lang).lower() for lang in supported_languages]:
        raise ValueError(
            f"Unsupported language: {language}. Supported languages are: {', '.join([str(lang) for lang in supported_languages])}"
        )

    # Convert mounts dictionary to a list of Mount objects if mounts is provided.
    mount_list: Optional[List[Mount]] = None
    if mounts:
        mount_list = []
        for container_path, host_path in mounts.items():
            if not os.path.isabs(host_path):
                raise ValueError("Each host path in mounts must be an absolute path.")
            mount_list.append(Mount(target=container_path, source=host_path, type="bind"))

    # Create and run the sandbox session with mounts for volume sharing.
    with SandboxSession(dockerfile=dockerfile, lang=language, mounts=mount_list, verbose=True) as session:
        # Optionally install libraries.
        if libraries:
            session.run("", libraries=libraries)
        # Execute the provided command.
        result = session.execute_command(command)

    return result.text
