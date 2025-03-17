from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError

from database.database import Database
from database.entities.projects import Project
from utils.logs.logging_utils import logger


class ProjectService:
    """
    Service class for managing Project operations.
    """

    def __init__(self):
        logger.debug("Initializing ProjectService.")
        try:
            self.db_session = Database.get_db_session()
            logger.info("ProjectService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ProjectService: {e}")
            raise

    def create_project(self, project: Project) -> None:
        """
        Creates a new project record in the database.

        Args:
            project (Project): The Project instance to be created.
        """
        logger.info(f"Creating project: {project}")
        try:
            self.db_session.add(project)
            self.db_session.commit()
            logger.info(f"Project created successfully: {project}")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error creating project: {e}")
            raise

    def get_project_by_id(self, project_id: int, user_id: int) -> Optional[Project]:
        """
        Retrieves a project by its ID.

        Args:
            project_id (int): The ID of the project to retrieve.
            user_id (int): The ID of the user who owns the project.

        Returns:
            Optional[Project]: The Project instance if found, else None.
        """
        logger.info(f"Retrieving project with ID: {project_id} for user ID: {user_id}")
   
        try:
            project = self.db_session.query(Project).filter(Project.id == project_id, Project.created_by == user_id).first()
            if project:
                logger.info(f"Project retrieved successfully: {project}")
            else:
                logger.warning(f"No project found with ID: {project_id} for user ID: {user_id}")
            return project
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving project with ID {project_id} for user ID {user_id}: {e}")
            raise

    def update_project(self, updated_project: Project) -> Optional[Project]:
        """
        Updates an existing project record using a Project object.

        Args:
            updated_project (Project): The Project instance with updated data.

        Returns:
            Optional[Project]: The updated Project instance if successful, else None.
        """
        logger.info(f"Updating project with ID: {updated_project.id}")
        try:
            existing_project = self.get_project_by_id(updated_project.id)
            if not existing_project:
                logger.warning(f"No project found with ID: {updated_project.id} to update.")
                return None

            updateable_fields = {
                'project_name',
                'project_description',
                'updated_by',
            }

            for key in updateable_fields:
                if hasattr(updated_project, key):
                    setattr(existing_project, key, getattr(updated_project, key))

            self.db_session.commit()
            self.db_session.refresh(existing_project)
            logger.info(f"Project updated successfully: {existing_project}")
            return existing_project
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error updating project with ID {updated_project.id}: {e}")
            raise

    def delete_project(self, project_id: int) -> bool:
        """
        Deletes a project record.

        Args:
            project_id (int): The ID of the project to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        logger.info(f"Deleting project with ID: {project_id}")
        try:
            project = self.get_project_by_id(project_id)
            if not project:
                logger.warning(f"No project found with ID: {project_id} to delete.")
                return False

            self.db_session.delete(project)
            self.db_session.commit()
            logger.info(f"Project with ID {project_id} deleted successfully.")
            return True
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Error deleting project with ID {project_id}: {e}")
            raise

    def get_projects(self, user_id: int) -> List[Project]:
        """
        Retrieves all projects created by a specific user.

        Args:
            user_id (int): The ID of the user.

        Returns:
            list: A list of Project instances.
        """
        logger.info(f"Retrieving all projects for user ID: {user_id}")
        try:
            projects = self.db_session.query(Project).filter(
                Project.created_by == user_id
            ).all()
            logger.info(f"Retrieved {len(projects)} projects for user ID: {user_id}")
            return projects
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving projects for user ID {user_id}: {e}")
            raise
