import sys
import time
from typing import List

from apis.microservice.controller import MicroserviceController
from apis.microservice_session.controller import MicroserviceSessionController
from apis.project.controller import ProjectController
from configs.project_config import ProjectAgents, ProjectGraphs
from database.entities.microservice_sessions import MicroserviceSession
from database.entities.microservices import Microservice
from genpod.team import TeamMembers
from utils.logs.logging_utils import logger
from utils.project_status import ProjectStatus


class ActionManager:
    def __init__(
        self,
        microservice: Microservice,
        agents: ProjectAgents,
        graphs: ProjectGraphs,
        database_path: str,
        collection_name: str,
        vector_db_path: str,
        graph_recursion_limit: int,
    ):
        logger.debug("Initializing ActionManager.")
        self.microservice = microservice
        self.agents = agents
        self.graphs = graphs
        self.database_path = database_path
        self.collection_name = collection_name
        self.vector_db_path = vector_db_path
        self.graph_recursion_limit = graph_recursion_limit
        self.microservice_controller = MicroserviceController()
        self.session_controller = MicroserviceSessionController()
        logger.info("ActionManager initialized successfully.")

    def setup_team_members(self):
        """Initialize and set up TeamMembers with the supervisor."""
        logger.info("Setting up team members.")
        try:
            self.genpod_team = TeamMembers(
                self.agents,
                self.graphs,
                self.database_path,
                self.collection_name,
                self.vector_db_path
            )
            self.genpod_team.supervisor.set_recursion_limit(self.graph_recursion_limit)
            self.genpod_team.supervisor.graph.agent.setup_team(self.genpod_team)
            logger.info("Team members set up successfully.")
        except Exception as e:
            logger.error(f"Failed to set up team members: {e}")
            raise

    def process_supervisor_response(self, supervisor_response):
        """Process the responses from the supervisor and update the microservice."""
        logger.info("Processing supervisor response.")
        try:
            should_update = False
            for res in supervisor_response:
                for node_name, super_state in res.items():
                    if self.microservice.microservice_name != super_state['microservice_name']:
                        self.microservice.microservice_name = super_state['microservice_name']
                        should_update = True

                    if self.microservice.status != str(super_state['project_status']):
                        self.microservice.status = str(super_state['project_status'])
                        should_update = True

                    if should_update:
                        self.microservice_controller.update(self.microservice)
                        logger.info(f"Microservice updated: {self.microservice}")
                        should_update = False
        except Exception as e:
            logger.error(f"Failed to process supervisor response: {e}")
            raise
    
    def stream_to_supervisor(self, data):
        """Stream data to the supervisor and return the response."""
        logger.info("Streaming data to supervisor.")
        try:
            response = self.genpod_team.supervisor.stream(data)
            logger.info("Data streamed to supervisor successfully.")
            return response
        except Exception as e:
            logger.error(f"Failed to stream data to supervisor: {e}")
            raise


class Action:

    def __init__(
        self,
        agents: ProjectAgents,
        graphs: ProjectGraphs,
        database_path: str,
        collection_name: str,
        vector_db_path: str,
        graph_recursion_limit: int
    ):
        
        self.agents = agents
        self.graphs = graphs
        self.database_path = database_path
        self.collection_name = collection_name
        self.vector_db_path = vector_db_path
        self.graph_recursion_limit = graph_recursion_limit
    
    def generate(self, microservice: Microservice):
        """Generate the microservice."""

        logger.info("Generating microservice.")
        user_prompt = Action._prompt_user_for_project_idea()
        try:
            manager = ActionManager(
                microservice,
                self.agents,
                self.graphs,
                self.database_path,
                self.collection_name,
                self.vector_db_path,
                self.graph_recursion_limit
            )

            manager.microservice.prompt = user_prompt
            manager.microservice_controller.create(manager.microservice)
            logger.info(f"Microservice created: {manager.microservice}")

            for agent in manager.agents:
                curr_session = MicroserviceSession(
                    agent_id=agent.agent_id,
                    project_id=manager.microservice.project_id,
                    microservice_id=manager.microservice.id,
                    created_by=manager.microservice.created_by,
                    updated_by=manager.microservice.created_by
                )
                manager.session_controller.create(curr_session)
                agent.set_thread_id(curr_session.id)
                logger.info(f"Session created: {curr_session}")

            manager.setup_team_members()

            supervisor_data = {
                "project_id": manager.microservice.project_id,
                "microservice_id": manager.microservice.id,
                "original_user_input": user_prompt,
                "project_path": manager.microservice.project_location,
                "license_url": manager.microservice.license_file_url,
                "license_text": manager.microservice.license_text,
            }

            supervisor_response = manager.stream_to_supervisor(supervisor_data)
            manager.process_supervisor_response(supervisor_response)

            logger.info("Microservice generation completed successfully.")
            print(
                f"Your service was generated successfully! Project ID: {manager.microservice.project_id}, "
                f"Service ID: {manager.microservice.id}, "
                f"Service Name: {manager.microservice.microservice_name}, Location: {manager.microservice.project_location}."
            )
        except Exception as e:
            logger.error(f"Failed to generate microservice: {e}")
            raise

    def resume(self, user_id: int):
        """Resume an existing microservice project."""

        logger.info("Resuming microservice.")
        try:
            # picked_project_id = Action._get_project_details(user_id)
            # if not picked_project_id:
            #     print("No projects are available for this user.")
            #     return 
            picked_project_id = 1
            picked_microservice = Action._get_microservice_details(user_id, picked_project_id)
            if not picked_microservice:
                print("No active services available for this project.")
                return

            session_details = Action._get_session_details(user_id, picked_project_id, picked_microservice.id)
            if not session_details:
                print("No sessions found for this service.")
                return

            session_map = {session.agent_id: session for session in session_details}
            for agent in self.agents:
                curr_session = session_map.get(agent.agent_id)
                if curr_session:
                    agent.set_thread_id(curr_session.id)

            manager = ActionManager(
                picked_microservice,
                self.agents,
                self.graphs,
                self.database_path,
                self.collection_name,
                self.vector_db_path,
                self.graph_recursion_limit,
            )

            manager.setup_team_members()
            last_saved_state = manager.genpod_team.supervisor.get_last_saved_state()
            supervisor_response = manager.stream_to_supervisor(last_saved_state)
            manager.process_supervisor_response(supervisor_response)

            logger.info("Microservice resumed successfully.")
            print(
                f"Your service was resumed successfully! Project ID: {manager.microservice.project_id}, "
                f"Service ID: {manager.microservice.id}, "
                f"Service Name: {manager.microservice.microservice_name}, Location: {manager.microservice.project_location}."
            )
        except Exception as e:
            logger.error(f"Failed to resume microservice: {e}")
            raise

    def microservice_status(
        self,
        user_id: str,
        project_id: int,
        microservice_id: int
    ) -> None:
        """
        """
        try:
            session_controller = MicroserviceSessionController()
            microservice_controller = MicroserviceController()
            
            picked_microservice = microservice_controller.get_microservice(microservice_id)
            if not picked_microservice:
                logger.warning(f"No active service found for given ID: {microservice_id}")
                return

            session_details = Action._get_session_details(user_id, project_id, picked_microservice.id)
            if not session_details:
                print("No sessions found for this service.")
                return

            session_map = {session.agent_id: session for session in session_details}
            for agent in self.agents:
                curr_session = session_map.get(agent.agent_id)
                if curr_session:
                    agent.set_thread_id(curr_session.id)

            manager = ActionManager(
                picked_microservice,
                self.agents,
                self.graphs,
                self.database_path,
                self.collection_name,
                self.vector_db_path,
                self.graph_recursion_limit,
            )

            manager.setup_team_members()
            while True:
                last_saved_state = manager.genpod_team.supervisor.get_last_saved_state()
                project_status = ProjectStatus(last_saved_state)
                
                sys.stdout.write(project_status.display_project_status())
                sys.stdout.flush()

                time.sleep(5)
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            raise
        
    @staticmethod
    def _prompt_user_for_project_idea() -> str:
        """Prompt the user for a project idea and validate the input."""
        while True:
            try:
                logger.info("Prompting user for project idea.")
                print("\nEnter the prompt to define your project idea (at least 10 characters): ")
                user_prompt = input("> ").strip()
                if len(user_prompt) > 9:
                    print(f"\nPrompt accepted: {user_prompt}")
                    logger.info(f"User provided valid project idea: {user_prompt}")
                    return user_prompt
                else:
                    print("Invalid input. Please provide a detailed description of your project idea (at least 10 characters).")
                    logger.warning("User provided invalid project idea. Prompting again.")
            except Exception as e:
                logger.error(f"An error occurred while processing user input for project idea: {e}")
                print(f"An error occurred while processing your input: {e}")

    @staticmethod
    def _get_project_details(user_id: int) -> int:
        """Retrieve and validate project details for the given user."""
        logger.info(f"Retrieving project details for user ID: {user_id}")
        project_controller = ProjectController()
        try:
            user_projects = project_controller.get_projects(user_id)
            if not user_projects:
                logger.warning(f"No projects found for user ID: {user_id}")
                return

            Action._list_items(
                user_projects,
                lambda project: f"  - ID: {project.id}, Name: {project.project_name}",
                "Available Projects"
            )
            return Action._prompt_user(
                "Please enter the ID of the project you want to select",
                lambda project_id: any(p.id == project_id for p in user_projects),
                "Invalid project ID. Please try again."
            )
        except Exception as e:
            logger.error(f"An error occurred while retrieving project details for user ID {user_id}: {e}")
            raise

    @staticmethod
    def _get_microservice_details(user_id: int, project_id: int) -> Microservice:
        """Retrieve and validate microservice details for the given project."""
        logger.info(f"Retrieving microservice details for user ID: {user_id}, project ID: {project_id}")
        microservice_controller = MicroserviceController()
        try:
            microservices = microservice_controller.get_microservices_by_project_id(user_id, project_id)
            if not microservices:
                logger.warning(f"No microservices found for project ID: {project_id}")
                return

            active_microservices = [ms for ms in microservices if ms.status != "DONE"]
            if not active_microservices:
                logger.warning(f"No active microservices found for project ID: {project_id}")
                return

            Action._list_items(
                active_microservices,
                lambda ms: f"  - ID: {ms.id}, Name: {ms.microservice_name}, Status: {ms.status}",
                "Active Microservices"
            )
            selected_id = Action._prompt_user(
                "Please enter the ID of the microservice you want to resume",
                lambda ms_id: any(ms.id == ms_id for ms in active_microservices),
                "Invalid microservice ID. Please try again."
            )
            logger.info(f"User selected microservice ID: {selected_id}")
            return next(ms for ms in active_microservices if ms.id == selected_id)
        except Exception as e:
            logger.error(f"An error occurred while retrieving microservice details: {e}")
            raise

    @staticmethod
    def _get_session_details(user_id: int, project_id: int, microservice_id: int) -> List[MicroserviceSession]:
        """Retrieve session details for the given user, project, and microservice."""
        logger.info(f"Retrieving session details for user ID: {user_id}, project ID: {project_id}, microservice ID: {microservice_id}")
        session_controller = MicroserviceSessionController()
        try:
            sessions = session_controller.get_sessions(project_id, microservice_id, user_id)
            if not sessions:
                logger.warning(f"No sessions found for project ID: {project_id}, microservice ID: {microservice_id}")
                return
            logger.info(f"Retrieved {len(sessions)} sessions for project ID: {project_id}, microservice ID: {microservice_id}")
            return sessions
        except Exception as e:
            logger.error(f"An error occurred while retrieving session details: {e}")
            raise

    @staticmethod
    def _list_items(items: List, display_func, title: str):
        """Display a list of items."""
        logger.info(f"Listing items under '{title}'")
        try:
            print(f"\n{title}:")
            for item in items:
                print(display_func(item))
            logger.info(f"Listed {len(items)} items under '{title}'")
        except Exception as e:
            logger.error(f"An error occurred while listing items: {e}")
            raise

    @staticmethod
    def _prompt_user(prompt: str, validate_func, error_message: str) -> int:
        """Prompt the user for input and validate it."""
        while True:
            try:
                user_input = int(input(f"{prompt}: ").strip())
                if validate_func(user_input):
                    logger.info(f"User input accepted: {user_input}")
                    return user_input
                else:
                    logger.warning(f"Invalid input: {user_input}. Prompting user again.")
                    print(error_message)
            except ValueError:
                logger.warning("Invalid input type provided. Expected an integer.")
                print("Invalid input. Please enter a valid integer.")
            except Exception as e:
                logger.error(f"An error occurred while prompting user: {e}")
                raise
