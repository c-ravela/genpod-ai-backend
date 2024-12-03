from datetime import datetime


class Project:
    
    id: int # unique identifier of the record
    project_name: str = "" # name of the project
    input_prompt: str # input prompt used for the project
    status: str = "" # status of the project generation
    license_text: str # user given license text for the project
    license_file_url: str # user given license file url
    project_location: str # path where project is located
    created_at: datetime # timestamp of when record is created
    updated_at: datetime # timestamp of the records last update
    created_by: int # user id of who created the record
    updated_by: int # user id of the who has updated this record at last

    def __init__(
        self,
        project_name: str,
        input_prompt: str,
        license_text: str,
        license_file_url: str,
        project_path: str,
        created_by: int,
    ):

        self.project_name = project_name
        self.input_prompt = input_prompt
        self.license_text = license_text
        self.license_file_url = license_file_url
        self.project_location = project_path
        self.created_by = created_by
