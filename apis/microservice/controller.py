from typing import List
from apis.microservice.entity import Microservice
from apis.microservice.service import MicroserviceService


class MicroserviceController:

    def __init__(self):
        self.microservice_service = MicroserviceService()

    def create(self, microservice: Microservice) -> Microservice:
        return self.microservice_service.create_microservice(microservice)
    
    def update(self, microservice: Microservice, user_id: int) -> Microservice:
        return self.microservice_service.update_microservice(microservice, user_id)
    
    def get_microservices(self, project_id: int, user_id: int) -> List[Microservice]:
        return self.microservice_service.get_microservices(project_id, user_id)
