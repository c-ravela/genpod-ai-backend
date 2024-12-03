from typing import List, Dict, Any

from apis.microservice.entity import Microservice
from database.database import Database


class MicroserviceService:
    """
    """

    def __init__(self):
        self.microservice_repository = Database.get_instance().microservices_table

    def create_microservice(self, microservice: Microservice) -> Microservice:

        microservice = self.microservice_repository.insert(
            microservice_name=microservice.microservice_name,
            project_id=microservice.project_id,
            status=microservice.status,
            user_id=microservice.created_by
        )

        return self.__to_Microservice(microservice)
    
    def update_microservice(self, microservice: Microservice, user_id: int) -> Microservice:

        microservice = self.microservice_repository.update(
            microservice.id,
            microservice_name=microservice.microservice_name,
            status=microservice.status,
            updated_by=user_id
        )

        return self.__to_Microservice(microservice)
    
    def get_microservices(self, project_id: int, user_id: int) -> List[Microservice]:

        return self.__get_microservices(project_id, user_id)
    
    def __get_microservices(self, project_id: int, user_id: int) -> List[Microservice]:

        query = f"SELECT * FROM microservices WHERE project_id=? AND created_by=?"
        microservices = []

        try:
            cursor = self.microservice_repository.connection.cursor()
            cursor.execute(query, (project_id, user_id,))
            rows = cursor.fetchall()

            for row in rows:
                record = {column[0]: row[i] for i, column in enumerate(cursor.description)}
                microservices.append(self.__to_Microservice(record))

            return microservices
        except Exception as e:
            raise
        finally:
            if cursor:
                cursor.close()
    
    @staticmethod
    def __to_Microservice(microservice: Dict[str, Any]) -> Microservice:

        m = Microservice(
            microservice_name=microservice['microservice_name'],
            project_id=microservice['project_id'],
            status=microservice['status'],
            created_by=microservice['created_by']
        )

        m.id = microservice['id']
        m.created_at = microservice['created_at']
        m.updated_at = microservice['updated_at']
        m.updated_by = microservice['updated_by']

        return m
