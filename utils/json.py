import json

class Json:
    def read_input_json(file_path) -> str:
        """Reads JSON data from a file and returns it as a string.

        Args:
            file_path: The path to the JSON file.

        Returns:
            A string representation of the JSON data.
        """
        with open(file_path, 'r') as user_input_file:
            data = json.load(user_input_file)
        
        user_input = json.dumps(data)
        license_txt = data["LICENSE_TEXT"]

        return user_input, license_txt