import sys
import time
from typing import List, Optional

from agents.rag import RAGAgent
from agents.rag_middleware import RAGMiddleware, register_rag_agent
from agents.supervisor import SupervisorAgent, SupervisorInput
from apis.microservice.controller import MicroserviceController
from apis.microservice_session.controller import MicroserviceSessionController
from apis.project.controller import ProjectController
from configs.project_config import AgentRegistry, RAGAgentRegistry
from context.context import GenpodContext
from database.entities.microservice_sessions import MicroserviceSession
from database.entities.microservices import Microservice
from database.entities.projects import Project
from genpod import Team
from models.constants import PStatus
from utils.logs.logging_utils import logger
from utils.project_status import ProjectStatus


class ActionManager:
    """
    Manager class for handling microservice actions including team member setup,
    supervisor interactions, and RAG (Retrieval-Augmented Generation) setup.
    """
    def __init__(
        self,
        microservice: Microservice,
        agent_registry: AgentRegistry,
        rag_agent_registry: RAGAgentRegistry,
        database_path: str,
        graph_recursion_limit: int,
    ):
        """
        Initialize the ActionManager.

        Args:
            microservice (Microservice): The microservice instance.
            agent_registry (AgentRegistry): Registry containing agent information.
            rag_agent_registry (RAGAgentRegistry): Registry for RAG agents.
            database_path (str): Path to the persistence database.
            graph_recursion_limit (int): Maximum recursion limit for graph operations.
        """
        logger.debug("Initializing ActionManager.")
        self.microservice = microservice
        self.agent_registry = agent_registry
        self.rag_agent_registry = rag_agent_registry
        self.database_path = database_path
        self.graph_recursion_limit = graph_recursion_limit
        self.microservice_controller = MicroserviceController()
        self.session_controller = MicroserviceSessionController()
        self._genpod_context = GenpodContext.get_context()
        self.is_rag_enabled = False
        self.supervisor = None
        logger.info("ActionManager initialized successfully.")

    def setup_team_members(self):
        """
        Initialize and set up team members and the supervisor.

        This method creates sessions for each team member in the team and for the supervisor,
        updates the GenpodContext with the session IDs, and configures the supervisor with the team.

        Raises:
            Exception: Propagates any exceptions encountered during team setup.
        """
        logger.info("Setting up team members.")
        try:
            self.genpod_team = Team(
                self.agent_registry,
                self.database_path
            )

            agents_session: dict[str, int] = {}
            for member in self.genpod_team.get_team_members():
                session = MicroserviceSession(
                    agent_id=member.id,
                    project_id=self.microservice.project_id,
                    microservice_id=self.microservice.id,
                    created_by=self.microservice.created_by,
                    updated_by=self.microservice.created_by
                )
                self.session_controller.create(session)
                member.set_thread_id(session.id)
                agents_session[member.id] = session.id
                logger.info(f"Session created for team member '{member.id}': {session}")

            supervisor_details = self.agent_registry.supervisor
            supervisor = SupervisorAgent(
                id=supervisor_details.agent_id,
                name=supervisor_details.agent_name,
                description=supervisor_details.description,
                llm=supervisor_details.llm,
                recursion_limit=self.graph_recursion_limit,
                persistence_db_path=self.database_path,
                use_rag=supervisor_details.use_rag
            )
            session = MicroserviceSession(
                agent_id=supervisor.id,
                project_id=self.microservice.project_id,
                microservice_id=self.microservice.id,
                created_by=self.microservice.created_by,
                updated_by=self.microservice.created_by
            )
            self.session_controller.create(session)
            supervisor.set_thread_id(session.id)
            agents_session[supervisor.id] = session.id
            logger.info(f"Session created for supervisor '{supervisor.id}': {session}")

            if not self._genpod_context.agents_session:
                self._genpod_context.update(agents_session=agents_session)
                logger.debug("GenpodContext.agents_session was empty; set to new sessions.")
            else:
                updated_sessions = {**self._genpod_context.agents_session, **agents_session}
                self._genpod_context.update(agents_session=updated_sessions)
                logger.debug("GenpodContext.agents_session updated with new sessions.")

            supervisor.setup_team(self.genpod_team)
            self.supervisor = supervisor

            logger.info("Team members set up successfully.")
        except Exception as e:
            logger.error(f"Error during team setup: {e}")
            raise

    def process_supervisor_response(self, supervisor_response):
        """
        Process supervisor responses and update the microservice if necessary.

        This method aggregates the supervisor's responses and, if any differences in the
        microservice's name or project status are detected, updates the microservice accordingly.

        Args:
            supervisor_response (list[dict[str, any]]): List of response dictionaries from the supervisor.

        Raises:
            Exception: Propagates any exceptions encountered during processing.
        """
        logger.info("Processing supervisor response.")
        try:
            new_microservice_name = self.microservice.microservice_name
            new_project_status = self.microservice.status

            for res in supervisor_response:
                for node_name, super_state in res.items():
                    if 'microservice_name' in super_state and new_microservice_name != super_state['microservice_name']:
                        new_microservice_name = super_state['microservice_name']
                    if 'project_status' in super_state and new_project_status != str(super_state['project_status']):
                        new_project_status = str(super_state['project_status'])
            
            if (new_microservice_name != self.microservice.microservice_name or
                new_project_status != self.microservice.status):
                logger.debug(
                    f"Updating microservice: name from '{self.microservice.microservice_name}' "
                    f"to '{new_microservice_name}', status from '{self.microservice.status}' "
                    f"to '{new_project_status}'."
                )
                self.microservice.microservice_name = new_microservice_name
                self.microservice.status = new_project_status
                self.microservice_controller.update(self.microservice)
                logger.info(f"Microservice updated: {self.microservice}")
            else:
                logger.debug("No updates required for microservice based on supervisor response.")
        except Exception as e:
            logger.error(f"Error processing supervisor response: {e}")
            raise

    def send_to_supervisor(self, data: SupervisorInput) -> any:
        """
        Send data to the supervisor and return its response.

        Args:
            data (SupervisorInput): The input data for the supervisor.

        Returns:
            any: The response from the supervisor.

        Raises:
            Exception: Propagates any exceptions encountered during data transmission.
        """
        logger.info("Sending data to supervisor.")
        try:
            response = self.supervisor.stream(data)
            logger.info("Data sent to supervisor successfully.")
            return response
        except Exception as e:
            logger.exception("Error sending data to supervisor.")
            raise
    
    def setup_rag(self):
        """
        Set up Retrieval-Augmented Generation (RAG) agents if not already enabled.

        This method registers RAG-related agents, creates sessions for them, and updates the GenpodContext
        with the new session IDs. After a successful setup, RAG functionality is marked as enabled.

        Raises:
            Exception: Propagates any exceptions encountered during RAG setup.
        """
        logger.info("Setting up RAG agents.")
        if not self.is_rag_enabled:
            try:
                rag_related_agents = []

                # Initialize the MISMO 3.6 RAG agent.
                mismo_3_6_rag_details = self.rag_agent_registry.mismo_3_6_rag
                mismo_3_6_rag = RAGAgent(
                    id=mismo_3_6_rag_details.agent_id,
                    name=mismo_3_6_rag_details.agent_name,
                    description=mismo_3_6_rag_details.description,
                    llm=mismo_3_6_rag_details.llm,
                    collection_name=mismo_3_6_rag_details.collection_name,
                    persist_directory=mismo_3_6_rag_details.vector_database_path,
                    recursion_limit=mismo_3_6_rag_details.recursion_limit,
                    persistance_db_path=self.database_path
                )
                register_rag_agent(mismo_3_6_rag, mismo_3_6_rag_details.description)
                rag_related_agents.append(mismo_3_6_rag)

                # Initialize the RAG middleware agent.
                rag_middleware_details = self.agent_registry.rag_middleware
                rag_middleware = RAGMiddleware(
                    id=rag_middleware_details.agent_id,
                    name=rag_middleware_details.agent_name,
                    description=rag_middleware_details.description,
                    llm=rag_middleware_details.llm,
                    recursion_limit=rag_middleware_details.recursion_limit,
                    persistence_db_path=self.database_path,
                )
                rag_related_agents.append(rag_middleware)

                rag_agents_session: dict[str, int] = {}
                for agent in rag_related_agents:
                    session = MicroserviceSession(
                        agent_id=agent.id,
                        project_id=self.microservice.project_id,
                        microservice_id=self.microservice.id,
                        created_by=self.microservice.created_by,
                        updated_by=self.microservice.created_by
                    )
                    self.session_controller.create(session)
                    agent.set_thread_id(session.id)
                    rag_agents_session[agent.id] = session.id
                    logger.info(f"Session created for RAG agent '{agent.id}': {session}")
                
                # Update the GenpodContext with RAG sessions.
                if not self._genpod_context.agents_session:
                    self._genpod_context.update(agents_session=rag_agents_session)
                    logger.debug("GenpodContext.agents_session was empty; set to new RAG sessions.")
                else:
                    updated_sessions = {**self._genpod_context.agents_session, **rag_agents_session}
                    self._genpod_context.update(agents_session=updated_sessions)
                    logger.debug("GenpodContext.agents_session updated with new RAG sessions.")

                self.is_rag_enabled = True
                logger.info("RAG agents set up successfully.")
            except Exception as e:
                logger.exception("Error during RAG setup.")
                raise
        else:
            logger.info("RAG agents are already enabled; skipping setup.")


class Action:
    """
    Action class responsible for managing projects and microservice operations.

    This includes creating projects, generating microservices, resuming microservices,
    and continuously monitoring service status. User interactions for input validation
    are also handled by this class.
    """

    def __init__(
        self,
        agents: AgentRegistry,
        rag_agents: RAGAgentRegistry,
        database_path: str,
        graph_recursion_limit: int
    ):
        """
        Initialize the Action instance.

        Args:
            agents (AgentRegistry): Registry of agents for microservice operations.
            rag_agents (RAGAgentRegistry): Registry of RAG (Retrieval-Augmented Generation) agents.
            database_path (str): File system path to the persistence database.
            graph_recursion_limit (int): Recursion limit for graph-based operations.
        """
        self._genpod_context = GenpodContext.get_context()
        self.agents = agents
        self.rag_agents = rag_agents
        self.database_path = database_path
        self.graph_recursion_limit = graph_recursion_limit
    
    def add_project(self, user_id: int):
        """
        Add a new project to the system based on user-provided inputs.

        Prompts the user for the project name and description, validates the inputs,
        creates a new Project instance, and persists it via the ProjectController.

        Args:
            user_id (int): The ID of the user creating the project.

        Raises:
            Exception: Propagates any errors encountered during project creation.
        """
        logger.info("Starting to add a new project.")
        project_controller = ProjectController()

        try:
            project_name = self._prompt_for_input("Enter the project name (at least 3 characters)", min_length=3)
            project_description = self._prompt_for_input("Enter the project description (at least 10 characters)", min_length=10)

            new_project = Project(
                project_name=project_name,
                project_description=project_description,
                created_by=user_id,
                updated_by=user_id
            )
            project_controller.create(new_project)

            logger.info(f"Project '{new_project.project_name}' created successfully.")
            print(f"Project '{new_project.project_name}' (ID: {new_project.id}) has been successfully created.")
        except Exception as e:
            logger.error(f"Failed to add project: {e}")
            raise

    def generate(self, project_id: int, user_id: int, project_path: str, license_header: str, license_url: str):
        """
        Generate a new microservice for a given project.

        This method retrieves project details, creates a new Microservice,
        initializes an ActionManager to set up team members and RAG agents,
        sends the user's project idea to the supervisor, and processes the supervisor's response.

        Args:
            project_id (int): The ID of the project for which the microservice is generated.
            user_id (int): The ID of the user generating the microservice.
            project_path (str): File system path where the project resides.
            license_header (str): License header text for the microservice.
            license_url (str): URL pointing to the license file.

        Raises:
            ValueError: If the specified project is not found.
            Exception: Propagates any other errors encountered during microservice generation.
        """
        logger.info("Starting microservice generation.")
        try:
            project = self._get_project(project_id, user_id)
            if project is None:
                raise ValueError("Project not found.")
            
            microservice = Microservice(
                project_id=project.id,
                status=str(PStatus.NEW),
                project_location=project_path,
                license_text=license_header,
                license_file_url=license_url,
                created_by=user_id,
                updated_by=user_id
            )

            manager = ActionManager(
                microservice,
                self.agents,
                self.rag_agents,
                self.database_path,
                self.graph_recursion_limit
            )
            
            user_prompt = Action._prompt_user_for_project_idea()
            manager.microservice.prompt = user_prompt
            manager.microservice_controller.create(manager.microservice)
            logger.info(f"Microservice created with ID {manager.microservice.id} for project ID {manager.microservice.project_id}.")

            self._genpod_context.update(user_prompt=user_prompt)
            logger.debug("GenpodContext updated with user_prompt: %s", user_prompt)

            delay_seconds = 5
            print(
                f"Service registered with the database.\n"
                f"Assigned Service ID: {manager.microservice.id}\n"
                f"You can locate this service under Project ID: {manager.microservice.project_id}.\n"
                f"Service generation will begin in approximately {delay_seconds} seconds. Please wait..."
            )
            time.sleep(delay_seconds)

            manager.setup_team_members()
            manager.setup_rag()

            supervisor_data = SupervisorInput(
                user_prompt=user_prompt,
                project_directory=manager.microservice.project_location,
                project_id=manager.microservice.project_id,
                microservice_id=manager.microservice.id,
                license_header=manager.microservice.license_text,
                license_url=manager.microservice.license_file_url
            )

            supervisor_response = manager.send_to_supervisor(supervisor_data)
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
        """
        Resume an existing microservice project.

        Retrieves the project and microservice details for the user,
        reinitializes team members and RAG agents, and processes the supervisor's
        latest state to resume operations.

        Args:
            user_id (int): The ID of the user resuming the project.

        Raises:
            Exception: Propagates any errors encountered during the resume process.
        """
        logger.info("Resuming microservice.")
        try:
            picked_project_id = Action._get_project_details(user_id)
            if not picked_project_id:
                print("No projects are available for this user.")
                logger.warning("No projects found for the user during resume operation.")
                return

            picked_microservice = Action._get_microservice_details(user_id, picked_project_id)
            if not picked_microservice:
                print("No active services available for this project.")
                logger.warning("No active microservices found for the selected project.")
                return

            session_details = Action._get_session_details(user_id, picked_project_id, picked_microservice.id)
            if not session_details:
                print("No sessions found for this service.")
                logger.warning("No sessions found for the selected microservice.")
                return

            manager = ActionManager(
                picked_microservice,
                self.agents,
                self.rag_agents,
                self.database_path,
                self.graph_recursion_limit,
            )

            manager.setup_team_members()
            manager.setup_rag()

            last_saved_state = manager.supervisor.graph.get_last_saved_state()

            user_prompt = last_saved_state['user_prompt']
            self._genpod_context.update(user_prompt=user_prompt)
            logger.debug("GenpodContext updated with user_prompt: %s", user_prompt)

            supervisor_response = manager.send_to_supervisor(last_saved_state)
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
        user_id: int,
        project_id: int,
        microservice_id: int
    ) -> None:
        """
        Continuously display the status of a microservice.

        Retrieves the microservice and its session details, then enters a loop to
        periodically fetch and display the current project status via the supervisor.
        The loop runs indefinitely with a 5-second interval between updates.

        Args:
            user_id (int): The ID of the user checking the status.
            project_id (int): The ID of the project containing the microservice.
            microservice_id (int): The ID of the microservice to monitor.

        Raises:
            Exception: Propagates any errors encountered during status retrieval.
        """
        logger.info("Checking microservice status.")
        try:
            microservice_controller = MicroserviceController()
            picked_microservice = microservice_controller.get_microservice(microservice_id)
            if not picked_microservice:
                logger.warning(f"No active service found for microservice ID: {microservice_id}")
                print("No active service found for the provided microservice ID.")
                return

            session_details = Action._get_session_details(user_id, project_id, picked_microservice.id)
            if not session_details:
                print("No sessions found for this service.")
                logger.warning("No sessions found during status check.")
                return

            session_map = {session.agent_id: session.id for session in session_details}

            supervisor_details = self.agents.supervisor
            supervisor = SupervisorAgent(
                id=supervisor_details.agent_id,
                name=supervisor_details.agent_name,
                description=supervisor_details.description,
                llm=supervisor_details.llm,
                recursion_limit=self.graph_recursion_limit,
                persistence_db_path=self.database_path,
                use_rag=supervisor_details.use_rag
            )
            supervisor_thread_id = session_map.get(supervisor.id)
            if not supervisor_thread_id:
                logger.warning("No session found for the supervisor agent.")
                print("Supervisor session not found.")
                return
            supervisor.set_thread_id(session_map[supervisor.id])

            logger.info("Entering status update loop for microservice.")
            while True:
                last_saved_state = supervisor.graph.get_last_saved_state()
                project_status = ProjectStatus(last_saved_state)
                
                sys.stdout.write(project_status.display_project_status())
                sys.stdout.flush()
                time.sleep(5)
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            raise

    @staticmethod
    def _prompt_user_for_project_idea() -> str:
        """
        Prompt the user for a project idea and validate the input.

        Returns:
            str: The validated project idea provided by the user.
        """
        return Action._prompt_for_input("Enter your project idea (at least 10 characters)", min_length=10)

    @staticmethod
    def _get_project_details(user_id: int) -> Optional[int]:
        """
        Retrieve and validate project details for the given user.

        Prompts the user to select a project from a list of available projects.

        Args:
            user_id (int): The ID of the user.

        Returns:
            Optional[int]: The selected project ID if available, else None.

        Raises:
            Exception: Propagates any errors encountered while retrieving projects.
        """
        logger.info(f"Retrieving project details for user ID: {user_id}")
        project_controller = ProjectController()
        try:
            user_projects = project_controller.get_projects(user_id)
            if not user_projects:
                logger.warning(f"No projects found for user ID: {user_id}")
                return None

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
            logger.exception(f"An error occurred while retrieving project details for user ID {user_id}.")
            raise

    @staticmethod
    def _get_microservice_details(user_id: int, project_id: int) -> Optional[Microservice]:
        """
        Retrieve and validate microservice details for the given project.

        Lists active microservices (i.e. those not marked as "DONE") and prompts the user
        to select one for resuming.

        Args:
            user_id (int): The ID of the user.
            project_id (int): The ID of the project.

        Returns:
            Optional[Microservice]: The selected Microservice if available, else None.

        Raises:
            Exception: Propagates any errors encountered while retrieving microservices.
        """
        logger.info(f"Retrieving microservice details for user ID: {user_id}, project ID: {project_id}")
        microservice_controller = MicroserviceController()
        try:
            microservices = microservice_controller.get_microservices_by_project_id(user_id, project_id)
            if not microservices:
                logger.warning(f"No microservices found for project ID: {project_id}")
                return None

            active_microservices = [ms for ms in microservices if ms.status != "DONE"]
            if not active_microservices:
                logger.warning(f"No active microservices found for project ID: {project_id}")
                return None

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
            return next((ms for ms in active_microservices if ms.id == selected_id), None)
        except Exception as e:
            logger.exception("An error occurred while retrieving microservice details.")
            raise

    @staticmethod
    def _get_session_details(user_id: int, project_id: int, microservice_id: int) -> Optional[List[MicroserviceSession]]:
        """
        Retrieve session details for the specified user, project, and microservice.

        Args:
            user_id (int): The ID of the user.
            project_id (int): The ID of the project.
            microservice_id (int): The ID of the microservice.

        Returns:
            Optional[List[MicroserviceSession]]: A list of sessions if available, else None.

        Raises:
            Exception: Propagates any errors encountered during session retrieval.
        """
        logger.info(f"Retrieving session details for user ID: {user_id}, project ID: {project_id}, microservice ID: {microservice_id}")
        session_controller = MicroserviceSessionController()
        try:
            sessions = session_controller.get_sessions(project_id, microservice_id, user_id)
            if not sessions:
                logger.warning(f"No sessions found for project ID: {project_id}, microservice ID: {microservice_id}")
                return None
            logger.info(f"Retrieved {len(sessions)} sessions for project ID: {project_id}, microservice ID: {microservice_id}")
            return sessions
        except Exception as e:
            logger.exception("An error occurred while retrieving session details.")
            raise

    @staticmethod
    def _list_items(items: List, display_func, title: str):
        """
        Display a list of items to the user.

        Args:
            items (List): The list of items to display.
            display_func (Callable): Function that converts an item to its display string.
            title (str): Title under which items will be listed.

        Raises:
            Exception: Propagates any errors encountered during listing.
        """
        logger.info(f"Listing items under '{title}'.")
        try:
            print(f"\n{title}:")
            for item in items:
                print(display_func(item))
            logger.info(f"Listed {len(items)} items under '{title}'.")
        except Exception as e:
            logger.exception("An error occurred while listing items.")
            raise

    @staticmethod
    def _prompt_user(prompt: str, validate_func, error_message: str) -> int:
        """
        Prompt the user for integer input and validate it.

        Continuously prompts until a valid integer input is received.

        Args:
            prompt (str): The prompt message for the user.
            validate_func (Callable): A function to validate the user input.
            error_message (str): Error message to display if validation fails.

        Returns:
            int: The validated user input.

        Raises:
            Exception: Propagates any errors encountered during prompting.
        """
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
                logger.exception("An error occurred while prompting the user.")
                raise

    @staticmethod
    def _prompt_for_input(prompt_message: str, min_length: int) -> str:
        """
        Prompt the user for input and validate it based on a minimum length requirement.

        Args:
            prompt_message (str): The message displayed to prompt the user.
            min_length (int): Minimum required length for the input.

        Returns:
            str: The validated input string.

        Raises:
            Exception: Propagates any errors encountered during input.
        """
        while True:
            try:
                user_input = input(f"{prompt_message}: ").strip()
                if len(user_input) >= min_length:
                    logger.debug(f"User provided valid input: {user_input}")
                    return user_input
                else:
                    print(f"Input too short. Please enter at least {min_length} characters.")
            except Exception as e:
                logger.exception("Error during user input.")
                raise
    
    @staticmethod
    def _get_project(project_id: int, user_id: int) -> Optional[Project]:
        """
        Retrieve and validate project details for the specified user.

        Args:
            project_id (int): The ID of the project to retrieve.
            user_id (int): The ID of the user who owns the project.

        Returns:
            Optional[Project]: The retrieved Project instance if found, else None.

        Raises:
            Exception: Propagates any errors encountered during project retrieval.
        """
        logger.info(f"Retrieving project details for project ID: {project_id} and user ID: {user_id}")
        project_controller = ProjectController()
        try:
            user_project = project_controller.get_project(project_id, user_id=user_id)
            if not user_project:
                logger.warning(f"No project found with ID: {project_id} for user ID: {user_id}")
                return None

            logger.info(f"Project details: ID={user_project.id}, Name={user_project.project_name}")
            return user_project
        except Exception as e:
            logger.exception("An error occurred while retrieving project details.")
            raise
