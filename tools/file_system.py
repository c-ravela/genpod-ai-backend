class FS:
    @staticmethod
    def read_file(path: str) -> str:
        """
        Returns the content of the file at the given path.
        Raises an exception if the file cannot be found or read.
        
        :param path: The path to the file
        :return: The content of the file as a string
        """
        try:
            with open(path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"The file at {path} was not found.")
        except Exception as e:
            raise Exception(f"An error occurred while reading the file at {path}: {str(e)}")
