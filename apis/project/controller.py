from typing import List
from apis.project.service import ProjectService
from apis.project.entity import Project

class ProjectController:
    """
    """

    def __init__(self):
        self.project_service = ProjectService()

    def create(self, project: Project) -> Project:
        return self.project_service.create_project(project)

    def update(self, project: Project, user_id: int) -> Project:
        return self.project_service.update_project(project, user_id)
    
    def get_projects(self, user_id: int) -> List[Project]:
        return self.project_service.get_projects(user_id)
