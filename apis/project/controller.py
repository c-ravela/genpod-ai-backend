from typing import List, Optional

from apis.project.service import ProjectService
from database.entities.projects import Project
from utils.logs.logging_utils import logger


class ProjectController:
    """
    Controller class for handling Project-related API requests.
    """

    def __init__(self):
        logger.debug("Initializing ProjectController.")
        self.project_service = ProjectService()
        logger.info("ProjectController initialized successfully.")

    def create(self, project: Project) -> None:
        """
        Creates a new project.

        Args:
            project (Project): The Project instance to create.
        """
        logger.info(f"Creating a new project: {project}")
        try:
            self.project_service.create_project(project)
            logger.info(f"Project created successfully: {project}")
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise

    def update(self, project: Project) -> Optional[Project]:
        """
        Updates an existing project.

        Args:
            project (Project): The Project instance with updated data.

        Returns:
            Optional[Project]: The updated Project instance if successful, else None.
        """
        logger.info(f"Updating project: {project}")
        try:
            updated_project = self.project_service.update_project(project)
            if updated_project:
                logger.info(f"Project updated successfully: {updated_project}")
            else:
                logger.warning(f"Project update returned None for project: {project}")
            return updated_project
        except Exception as e:
            logger.error(f"Failed to update project: {e}")
            raise
    
    def delete(self, project_id: int) -> bool:
        """
        Deletes a project.

        Args:
            project_id (int): The ID of the project to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        logger.info(f"Deleting project with ID: {project_id}")
        try:
            result = self.project_service.delete_project(project_id)
            if result:
                logger.info(f"Project with ID {project_id} deleted successfully.")
            else:
                logger.warning(f"Project with ID {project_id} could not be deleted.")
            return result
        except Exception as e:
            logger.error(f"Failed to delete project with ID {project_id}: {e}")
            raise

    def get_projects(self, user_id: int) -> List[Project]:
        """
        Retrieves all projects for a specific user.

        Args:
            user_id (int): The ID of the user.

        Returns:
            List[Project]: A list of Project instances.
        """
        logger.info(f"Retrieving all projects for user ID: {user_id}")
        try:
            projects = self.project_service.get_projects(user_id)
            logger.info(f"Retrieved {len(projects)} projects for user ID: {user_id}")
            return projects
        except Exception as e:
            logger.error(f"Failed to retrieve projects for user ID {user_id}: {e}")
            raise

    def get_project(self, project_id: int) -> Optional[Project]:
        """
        Retrieves a single project by ID.

        Args:
            project_id (int): The ID of the project.

        Returns:
            Optional[Project]: The Project instance if found, else None.
        """
        logger.info(f"Retrieving project with ID: {project_id}")
        try:
            project = self.project_service.get_project_by_id(project_id)
            if project:
                logger.info(f"Project retrieved successfully: {project}")
            else:
                logger.warning(f"No project found with ID: {project_id}")
            return project
        except Exception as e:
            logger.error(f"Failed to retrieve project with ID {project_id}: {e}")
            raise
