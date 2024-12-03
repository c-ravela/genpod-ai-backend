from typing import Any, Dict, List

from apis.session.entity import Session
from database.database import Database


class SessionService:

    def __init__(self):
        self.session_repository = Database.get_instance().sessions_table

    
    def create_session(self, session: Session) -> Session:
        new_session = self.session_repository.insert(
            project_id=session.project_id,
            agent_id=session.agent_id,
            microservice_id=session.microservice_id,
            user_id=session.created_by
        )

        return self.__to_Session(new_session)
    
    def get_sessions(self, project_id: int, microservice_id: int, user_id: int) -> List[Session]:
        return self.__get_sessions(project_id, microservice_id, user_id)
    
    def __get_sessions(self, project_id: int, microservice_id: int, user_id: int) -> List[Session]:

        query = f"SELECT * FROM sessions WHERE project_id=? AND microservice_id=? AND created_by=?"
        sessions = []
        try:
            cursor = self.session_repository.connection.cursor()
            cursor.execute(query, (project_id, microservice_id, user_id,))
            rows = cursor.fetchall()

            for row in rows:
                record = {column[0]: row[i] for i, column in enumerate(cursor.description)}
                sessions.append(self.__to_Session(record))

            return sessions
        except Exception as e:
            raise
        finally:
            if cursor:
                cursor.close()
    
    @staticmethod
    def __to_Session(session: Dict[str, Any]) -> Session:
        s = Session(
            agent_id=session['agent_id'],
            project_id=session['project_id'],
            microservice_id=session['microservice_id'],
            created_by=session['created_by']
        )

        s.id = session['id']
        s.created_at = session['created_at']
        s.updated_at = session['updated_at']
        s.updated_by = session['updated_by']

        return s
