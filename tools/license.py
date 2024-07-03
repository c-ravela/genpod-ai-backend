"""
This module provides a tool for downloading and saving license files from a given URL.
"""

from langchain.tools import tool

from typing import Annotated

import os
import requests

class License:
    """
    A class used to represent a License.

    This class provides a method to download a license file from a given URL and save it locally.
    """

    @tool
    def download_license_file(
            url: Annotated[
                str, 
                "The URL from where the license file has to be downloaded."
            ],
            file_path: Annotated[
                str, 
                "The absolute path where the downloaded license file should be "
                "saved. This method can handle directory creation if it does not exist."
            ]
    ) -> tuple[bool, str]:
        """
        Downloads a license file from a given URL and saves it locally.

        Args:
            url (str): The URL from where the license file has to be downloaded.
            file_path (str): The absolute path where the downloaded license file 
            should be saved. This method can handle directory creation if it does 
            not exist.
        
        Returns:
            bool: True if tool failed to complete its task. Otherwise False.
            str: Success or failure message with local path where the file has
            to be written.
        """

        try:
            response = requests.get(url)

            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'wb') as file:
                file.write(response.content)
            return (False, f"License file successfully downloaded and stored at '{file_path}'.")

        except:
            return (True, f"Failed to download and store the license file at '{file_path}'.")
