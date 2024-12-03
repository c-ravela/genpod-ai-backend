from typing import List

from apis.session.entity import Session
from apis.session.service import SessionService


class SessionController:

    def __init__(self):
        self.session_service = SessionService()
    
    def create(self, session: Session) -> Session:
        return self.session_service.create_session(session)
    
    def get_sessions(self, project_id: int, microservice_id: int, user_id: int) -> List[Session]:
        return self.session_service.get_sessions(project_id, microservice_id, user_id)
    