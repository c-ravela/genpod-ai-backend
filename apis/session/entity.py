from datetime import datetime


class Session:
    id: int
    agent_id: str
    project_id: int
    microservice_id: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    def __init__(
        self,
        agent_id: str,
        project_id: int,
        microservice_id: int,
        created_by: int
    ):
        self.agent_id = agent_id
        self.project_id = project_id
        self.microservice_id = microservice_id
        self.created_by = created_by
    