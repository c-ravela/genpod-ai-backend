"""
This module provides a Shell class for executing shell commands on the local machine.

The Shell class is designed to execute a set of whitelisted commands securely and efficiently.
"""
import shlex
import subprocess
from typing import Annotated

from langchain.tools import tool

from configs.shell_config import CODER_COMMANDS, SHELL_COMMANDS_JOIN_SYMBOLS


class Shell:
    """
    The Shell class provides a method to execute shell commands on the local machine.
    """

    @tool
    def execute_command(
        command: Annotated[
            str, 
            "The command and its arguments to be run on the shell."
        ],
        repo_path: Annotated[
            str,
            "The absolute path to the repository where the command will be executed."
        ]
    ) -> tuple[bool, str]:
        """
        Executes a command on the local machine. This function is only allowed to use the 
        following commands:
        'mkdir, docker, python, python3, pip, virtualenv, mv, pytest, touch, cat, ls'

        The use of these symbols to concatenate or pipe commands is not permitted:
        '&&, ||, |, ;'

        Args:
            command (str): The command and its arguments to be run on the shell.
            repo_path(str): The absolute path to the repository where the command will be executed.

        Returns:
            tuple: A tuple where the first element is a boolean indicating whether an error occurred 
            (True if there was an error, False otherwise), and the second element is a string message. 
            
            If the command was executed successfully, the message includes the output of the command. 
            
            If there was an error, the message includes the error details.
        """

        # Split the command into parts
        parts = command.split()
        
        # Check if the command is in the whitelist
        if parts[0] not in CODER_COMMANDS:
            return (True, f"Operation Aborted! The command '{parts[0]}' is not recognized as a safe command.")
        
        # Check if the command contains any command joining symbols
        for symbol in SHELL_COMMANDS_JOIN_SYMBOLS:
            if symbol in command:
                return (True, f"Operation Aborted! The use of command joining symbol '{symbol}' is not permitted.")
        
        repo_path = shlex.quote(repo_path)
        command = shlex.quote(command)

        try:
            # Execute the command
            # full_path = os.path.join(PROJECT_PATH,repo_path)
            additional_command = f"cd {repo_path} && "
            updated_command = additional_command + command

            result = subprocess.check_output(updated_command, shell=True)
            
            return (False, f"Success! The command was executed successfully. Here's the output: \n'{result}'")
        except BaseException as e:
            return (True, f"Error! The command failed to execute. Here's the error message: \n'{repr(e)}'")
        