from typing import List, Dict, Any
from apis.project.entity import Project
from database.database import Database

class ProjectService:
    """
    """

    def __init__(self):
        """"""
        self.project_repository = Database.get_instance().projects_table

    def create_project(self, project: Project) -> Project:
        new_project = self.project_repository.insert(
            project_name=project.project_name,
            input_prompt=project.input_prompt,
            status=project.status,
            project_location=project.project_location,
            user_id=project.created_by,
            license_text=project.license_text,
            license_file_url=project.license_file_url
        )

        return self.__to_Project(new_project)
    
    def update_project(self, project: Project, user_id: int) -> Project:
        """
        """

        updated_project = self.project_repository.update(
            project.id,
            project_name=project.project_name,
            status=project.status,
            updated_by=user_id
        )
        
        return self.__to_Project(updated_project)

    def get_projects(self, user_id: int) -> List[Project]:
        """
        """

        return self.__get_projects(user_id)
    
    def __get_projects(self, user_id: int) -> List[Project]:
        """
        """

        query = f"SELECT * FROM projects WHERE created_by=?"
        projects = []
        try: 
            cursor = self.project_repository.connection.cursor()
            cursor.execute(query, (user_id,))
            rows = cursor.fetchall()

            for row in rows:
                record = {column[0]: row[i] for i, column in enumerate(cursor.description)}
                projects.append(self.__to_Project(record))

            return projects
        except Exception as e:
            raise
        finally:
            if cursor:
                cursor.close()
    
    @staticmethod
    def __to_Project(project: Dict[str, Any]) -> Project:

        p = Project(
            project['project_name'],
            project['input_prompt'],
            project['license_text'],
            project['license_file_url'],
            project['project_location'],
            project['created_by']
        )
        p.id = project['id']
        p.status = project['status']
        p.created_at = project['created_at']
        p.updated_at = project['updated_at']
        p.updated_by = project['updated_by']

        return p
