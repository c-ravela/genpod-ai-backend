from langchain.tools import tool

from typing import Annotated

import os
import requests

class License:

    @tool
    def download_license_file(
            url: Annotated[
                str, 
                "LICENSE_URL from where it has to be downloaded."
            ],
            file_path: Annotated[
                str, 
                "Absolute path where the License.md should be written can"
                "handle directory create if does not exist."
            ]
    ) -> tuple[bool, str]:
        """
        Downloads a license file from a given URL and saves it locally.

        Args:
            url (str): The URL of the license file.
            file_path (str): Absolute path where the generated code should be 
            written can handle directory create if does not exist.
        
        Returns:
            bool: True if tool failed to complete its task. Otherwise False.
            str: Success or failure message with local path where the file has
            to be written.
        """

        response = requests.get(url)
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'wb') as file:
                file.write(response.content)
            return (False, f"Successfully wrote the License to {file_path}")

        except:
            return (True, f"failed to write the License to {file_path}")
