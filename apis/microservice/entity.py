from datetime import datetime


class Microservice:

    id: int  # unique identifier of the record
    microservice_name: str  # name of the microservice
    project_id: int  # id of the project to which this microservice belongs to
    status: str  # status of this microservice generation
    created_at: datetime  # timestamp of when record is created
    updated_at: datetime  # timestamp of the records last update
    created_by: int  # user id of who created the record
    updated_by: int  # user id of the who has updated this record at last
    
    def __init__(
        self,
        microservice_name: str,
        project_id: int,
        status: str,
        created_by: int
    ):
        self.microservice_name = microservice_name
        self.project_id = project_id
        self.status = status
        self.created_by = created_by
