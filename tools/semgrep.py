import os
import subprocess

from langchain.tools import tool


class Semgrep:
    """
    This class defines tools for interacting with the Semgrep CLI.
    """

    _tool: str = "semgrep"

    def name(self) -> str:
        """
        """

        return self._tool
    
    def login(self, login_token: str) -> None:
        """
        Set the Semgrep application token for authentication.

        Args:
            login_token (str): The token used to authenticate with Semgrep.
        """

        os.environ['SEMGREP_APP_TOKEN'] = login_token
    
    def logout(self) -> subprocess.CompletedProcess:
        """
        Log out of the Semgrep CLI.

        Returns:
            subprocess.CompletedProcess: The result of the logout command or an error.
        """
        command = [self._tool, 'logout']

        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            return result
        except subprocess.CalledProcessError as e:
            return subprocess.CompletedProcess(args=command, returncode=e.returncode, stdout=e.stdout, stderr=e.stderr)
    
    def simple_scan(self, dir: str) -> subprocess.CompletedProcess:
        """
        Perform a simple scan of the specified directory.

        Args:
            dir (str): The directory to scan.

        Returns:
            subprocess.CompletedProcess: The result of the scan command or an error.
        """
        command = [self._tool, 'scan', dir, '--verbose']

        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            return result
        except subprocess.CalledProcessError as e:
            return subprocess.CompletedProcess(args=command, returncode=e.returncode, stdout=e.stdout, stderr=e.stderr)
    
    def pro_scan(self, dir: str) -> subprocess.CompletedProcess:
        """
        Perform a scan with pro rules on a specified directory.

        Args:
            dir (str): The directory to scan.

        Returns:
            subprocess.CompletedProcess: The result of the pro scan command or an error.
        """
        command = [self._tool, 'ci']

        try:
            result = subprocess.run(command, cwd=dir, check=True, capture_output=True, text=True)
            return result
        except subprocess.CalledProcessError as e:
            return subprocess.CompletedProcess(args=command, returncode=e.returncode, stdout=e.stdout, stderr=e.stderr)
