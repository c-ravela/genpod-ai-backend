import os
import time
from enum import Enum
from typing import List, Optional, Dict, Type, Any

from rich.live import Live

from agents.rag import RAGAgent
from agents.rag_middleware import RAGMiddleware, register_rag_agent
from agents.research import ResearchAgent
from agents.supervisor import SupervisorAgent, SupervisorInput
from apis.microservice.controller import MicroserviceController
from apis.microservice_llm_metrics.controller import \
    MicroserviceLLMMetricsController
from apis.microservice_session.controller import MicroserviceSessionController
from apis.project.controller import ProjectController
from configs.project_config import AgentRegistry, RAGAgentInfo, AgentInfo
from context.context import GenpodContext
from database.entities.microservice_sessions import MicroserviceSession
from database.entities.microservices import Microservice
from database.entities.projects import Project
from genpod import Team
from models.constants import PStatus
from utils.logger import logger
from utils.microservice_insights import MicroserviceInsights
from core.agent import BaseAgent


class MethodNames(Enum):
    ARCHITECT = "call_architect"
    PLANNER = "call_planner"
    CODER = "call_coder"
    TESTS_GENERATOR = "call_test_code_generator"
    REVIEWER = "call_reviewer"


def create_method_to_agent_mapping(agent_registry: AgentRegistry) -> dict:
    """
    Dynamically create the mapping between method names and agents.
    """
    return {
        method.value: getattr(agent_registry, method.name.lower())
        for method in MethodNames
    }


METHOD_TO_AGENT = create_method_to_agent_mapping(AgentRegistry)


class ActionManager:
    """
    Manager class for handling microservice actions including team member setup,
    supervisor interactions, and RAG (Retrieval-Augmented Generation) setup.
    """

    def __init__(
        self,
        microservice: Microservice,
        agent_registry: AgentRegistry,
        rag_agent_registry: Dict[str, RAGAgentInfo],
        database_path: str,
        graph_recursion_limit: int,
    ):
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
        self.supervisor: Optional[SupervisorAgent] = None
        self.genpod_team: Optional[Team] = None
        logger.info("ActionManager initialized successfully.")

    def _update_context_sessions(self, new_sessions: Dict[str, int]):
        """
        Merge new_sessions into GenpodContext.agents_session.
        """
        existing = self._genpod_context.agents_session or {}
        merged = {**existing, **new_sessions}
        self._genpod_context.update(agents_session=merged)
        logger.debug("GenpodContext.agents_session updated with new sessions.")

    def _create_session_for_agent(self, agent: BaseAgent) -> int:
        """
        Helper method to create a session for a given agent and return the session ID.
        """
        session = MicroserviceSession(
            agent_id=agent.id,
            project_id=self.microservice.project_id,
            microservice_id=self.microservice.id,
            created_by=self.microservice.created_by,
            updated_by=self.microservice.created_by
        )
        self.session_controller.create(session)
        agent.set_thread_id(session.id)
        logger.info(f"Session created for agent '{agent.id}': {session}")
        return session.id

    def _build_and_attach_agent(
        self,
        cls: Type[BaseAgent],
        info: AgentInfo,
        sessions: Dict[str, int],
        **extra_kwargs: Any
    ) -> BaseAgent:
        """
        Instantiate an Agent subclass, create its session, attach it, and return it.
        """
        agent = cls(
            id=info.agent_id,
            name=info.agent_name,
            description=info.description,
            llm=info.llm,
            recursion_limit=info.recursion_limit,
            persistence_db_path=self.database_path,
            **extra_kwargs
        )
        sessions[agent.id] = self._create_session_for_agent(agent)
        return agent

    def setup_team_members(self):
        """
        Initialize and set up team members and the supervisor.

        This method creates sessions for each team member in the team and for the supervisor,
        updates the GenpodContext with the session IDs, and configures the supervisor with the team.
        """
        logger.info("Setting up team members.")
        try:
            # Instantiate the genpod_team
            self.genpod_team = Team(self.agent_registry, self.database_path)
            sessions: Dict[str, int] = {}

            # Create sessions for each team member
            for member in self.genpod_team.get_team_members():
                sessions[member.id] = self._create_session_for_agent(member)

            # Build and attach the supervisor
            sup = self._build_and_attach_agent(
                SupervisorAgent,
                self.agent_registry.supervisor,
                sessions,
                use_rag=self.agent_registry.supervisor.use_rag
            )

            # Merge new sessions into context
            self._update_context_sessions(sessions)

            # Configure supervisor with the team
            sup.setup_team(self.genpod_team)
            self.supervisor = sup

            logger.info("Team members set up successfully.")
        except Exception as e:
            logger.error(f"Error during team setup: {e}")
            raise

    def process_supervisor_response(self, supervisor_response: List[dict]):
        """
        Process supervisor responses and update the microservice if necessary.
        """
        logger.info("Processing supervisor response.")
        try:
            new_microservice_name = self.microservice.microservice_name
            new_project_status = self.microservice.status

            for res in supervisor_response:
                for _, super_state in res.items():
                    if ('microservice_name' in super_state and
                            super_state['microservice_name'] != new_microservice_name):
                        new_microservice_name = super_state['microservice_name']
                    if ('project_status' in super_state and
                            str(super_state['project_status']) != new_project_status):
                        new_project_status = str(super_state['project_status'])

            if (new_microservice_name != self.microservice.microservice_name or
                    new_project_status != self.microservice.status):
                logger.debug(
                    f"Updating microservice: name '{self.microservice.microservice_name}'→"
                    f"'{new_microservice_name}', status '{self.microservice.status}'→"
                    f"'{new_project_status}'."
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

    def send_to_supervisor(self, data: SupervisorInput) -> Any:
        """
        Send data to the supervisor and return its response.
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
        """
        if self.is_rag_enabled:
            logger.info("RAG agents are already enabled; skipping setup.")
            return

        logger.info("Setting up RAG agents.")
        rag_sessions: Dict[str, int] = {}

        # Instantiate and register RAGAgents
        for info in self.rag_agent_registry.values():
            rag = RAGAgent(
                id=info.agent_id,
                name=info.agent_name,
                description=info.description,
                llm=info.llm,
                collection_name=info.collection_name,
                persist_directory=info.vector_database_path,
                recursion_limit=info.recursion_limit,
                persistence_db_path=self.database_path,
            )
            register_rag_agent(rag, info.description)
            rag_sessions[rag.id] = self._create_session_for_agent(rag)

        # Research Agent
        research = self._build_and_attach_agent(
            ResearchAgent,
            self.agent_registry.research,
            rag_sessions
        )

        # RAG Middleware
        mw_info = self.agent_registry.rag_middleware
        self._build_and_attach_agent(
            RAGMiddleware,
            mw_info,
            rag_sessions,
            research_agent=research,
            use_research_agent=True
        )

        # Merge new RAG sessions into context
        self._update_context_sessions(rag_sessions)

        self.is_rag_enabled = True
        logger.info("RAG agents set up successfully.")

    def rehydrate_rag(self, session_map: Dict[str, int]) -> None:
        """
        Rehydrate Retrieval Augmented Generation (RAG) agents from existing sessions.
        """
        if self.is_rag_enabled:
            return

        logger.info("Hydrating RAG agents from existing sessions.")
        # Rehydrate each RAGAgent
        for info in self.rag_agent_registry.values():
            tid = session_map.get(info.agent_id)
            if not tid:
                continue
            agent = RAGAgent(
                id=info.agent_id,
                name=info.agent_name,
                description=info.description,
                llm=info.llm,
                collection_name=info.collection_name,
                persist_directory=info.vector_database_path,
                recursion_limit=info.recursion_limit,
                persistence_db_path=self.database_path,
            )
            register_rag_agent(agent, info.description)
            agent.set_thread_id(tid)

        # ResearchAgent
        research_info = self.agent_registry.research
        research_tid = session_map.get(research_info.agent_id)
        research_agent = None
        if research_tid:
            research_agent = ResearchAgent(
                id=research_info.agent_id,
                name=research_info.agent_name,
                description=research_info.description,
                llm=research_info.llm,
                recursion_limit=research_info.recursion_limit,
                persistence_db_path=self.database_path
            )
            research_agent.set_thread_id(research_tid)

        # RAGMiddleware
        mw_info = self.agent_registry.rag_middleware
        mw_tid = session_map.get(mw_info.agent_id)
        if mw_tid:
            middleware = RAGMiddleware(
                id=mw_info.agent_id,
                name=mw_info.agent_name,
                description=mw_info.description,
                llm=mw_info.llm,
                research_agent=research_agent,
                recursion_limit=mw_info.recursion_limit,
                persistence_db_path=self.database_path,
                use_research_agent=bool(research_agent),
            )
            middleware.set_thread_id(mw_tid)

        self.is_rag_enabled = True
        logger.info("RAG agents rehydrated successfully.")

    def rehydrate_team(self, session_map: Dict[str, int]) -> None:
        """
        Rehydrate team members from existing sessions.
        """
        self.genpod_team = Team(self.agent_registry, self.database_path)
        for member in self.genpod_team.get_team_members():
            tid = session_map.get(member.id)
            if tid:
                member.set_thread_id(tid)

    def rehydrate_supervisor(self, session_map: Dict[str, int]) -> None:
        """
        Rehydrate the supervisor from existing sessions.
        """
        info = self.agent_registry.supervisor
        sup = SupervisorAgent(
            id=info.agent_id,
            name=info.agent_name,
            description=info.description,
            llm=info.llm,
            recursion_limit=self.graph_recursion_limit,
            persistence_db_path=self.database_path,
            use_rag=info.use_rag,
        )
        tid = session_map.get(sup.id)
        if tid:
            sup.set_thread_id(tid)
        self.supervisor = sup

    def run_supervisor_flow(self, init_data: Optional[SupervisorInput] = None):
        """
        Pull the last saved state from the supervisor graph,
        update context, resend to supervisor, and process the response.
        """
        payload = init_data or self.supervisor.graph.get_last_saved_state()
        prompt = getattr(payload, "user_prompt", "") or payload.get("user_prompt", "")

        # Update prompt in context
        self._genpod_context.update(user_prompt=prompt)

        # IMPORTANT: use the existing genpod_team (whether from setup or rehydrate)
        self.supervisor.setup_team(self.genpod_team)

        # Send & process
        response = self.send_to_supervisor(payload)
        self.process_supervisor_response(response)

    def microservice_insights(
        self,
        user_id: int,
        project_id: int,
        microservice_id: int
    ) -> None:
        """
        Continuously retrieve and display insights for a microservice.
        """
        logger.info("Starting to monitor microservice insights.")
        try:
            ms_ctrl = MicroserviceController()
            metrics_ctrl = MicroserviceLLMMetricsController()

            picked_microservice = ms_ctrl.get_microservice(microservice_id)
            if not picked_microservice:
                logger.warning(f"No active service for ID: {microservice_id}")
                print(f"No active service found for ID {microservice_id}.")
                return

            session_details = Action._get_session_details(user_id, project_id, picked_microservice.id)
            if not session_details:
                logger.warning("No sessions found for insights.")
                print("No sessions found for this service.")
                return
            session_map = {s.agent_id: s.id for s in session_details}

            sup_info = self.agent_registry.supervisor
            supervisor = SupervisorAgent(
                id=sup_info.agent_id,
                name=sup_info.agent_name,
                description=sup_info.description,
                llm=sup_info.llm,
                recursion_limit=self.graph_recursion_limit,
                persistence_db_path=self.database_path,
                use_rag=sup_info.use_rag
            )
            sup_tid = session_map.get(supervisor.id)
            if not sup_tid:
                logger.warning("Supervisor session not found for insights.")
                print("Supervisor session not found.")
                return
            supervisor.set_thread_id(sup_tid)

            _team = Team(self.agent_registry, self.database_path)
            insights = MicroserviceInsights({})

            with Live(insights.build_renderable(), screen=True, refresh_per_second=2) as live:
                while True:
                    last_saved_state = supervisor.graph.get_last_saved_state()
                    token_metrics = metrics_ctrl.get_token_metrics_by_microservice(
                        microservice_id, project_id, user_id
                    )
                    active_node = last_saved_state.get("active_node", "")
                    agent_info = METHOD_TO_AGENT.get("call_architect")
                    agent_state = None

                    if agent_info:
                        member = next(
                            (a for a in _team.get_team_members() if a.id == agent_info.agent_id),
                            None
                        )
                        tid = session_map.get(agent_info.agent_id)
                        if member and tid:
                            member.set_thread_id(tid)
                            agent_state = member.graph.get_last_saved_state()
                            agent_state["agent_name"] = agent_info.agent_name

                    insights.data = last_saved_state
                    insights.token_metrics = token_metrics
                    insights.current_agent = agent_state
                    live.update(insights.build_renderable())
                    time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Microservice insights monitoring stopped by user.")
        except Exception as e:
            logger.error(f"Error retrieving microservice insights: {e}")
            raise


class Action:
    """
    Action class responsible for managing projects and microservice operations.
    """

    def __init__(
        self,
        agents: AgentRegistry,
        rag_agents: Dict[str, RAGAgentInfo],
        database_path: str,
        graph_recursion_limit: int
    ):
        self._genpod_context = GenpodContext.get_context()
        self.agents = agents
        self.rag_agents = rag_agents
        self.database_path = database_path
        self.graph_recursion_limit = graph_recursion_limit

    def add_project(self, user_id: int):
        """
        Add a new project to the system based on user-provided inputs.
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

    def generate(
        self,
        project_id: int,
        user_id: int,
        project_path: str,
        license_header: str,
        license_url: str
    ):
        """
        Generate a new microservice for a given project.
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

            human_prompt = Action._prompt_user_for_project_generation(
                manual_prompt="Enter your project idea (at least 10 characters)",
                min_length=10,
            )

            final_human_input = f"Human Prompt: {human_prompt}"
            manager.microservice.prompt = final_human_input
            manager.microservice_controller.create(manager.microservice)
            logger.info(f"Microservice created with ID {manager.microservice.id} for project ID {manager.microservice.project_id}.")

            self._genpod_context.update(user_prompt=final_human_input)
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
                user_prompt=final_human_input,
                project_directory=manager.microservice.project_location,
                project_id=manager.microservice.project_id,
                microservice_id=manager.microservice.id,
                license_header=manager.microservice.license_text,
                license_url=manager.microservice.license_file_url
            )

            manager.run_supervisor_flow(supervisor_data)

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

            sessions = Action._get_session_details(user_id, picked_project_id, picked_microservice.id)
            if sessions is None:
                print("No sessions found for this service.")
                logger.warning("No sessions found for the selected microservice.")
                return
            session_map: Dict[str,int] = {s.agent_id: s.id for s in sessions}

            manager = ActionManager(
                picked_microservice,
                self.agents,
                self.rag_agents,
                self.database_path,
                self.graph_recursion_limit,
            )

            # Rehydrate flows
            self._genpod_context.update(agents_session=session_map)
            manager.rehydrate_team(session_map)
            manager.rehydrate_supervisor(session_map)
            manager.rehydrate_rag(session_map)

            # Run with the correct genpod_team attached
            manager.run_supervisor_flow()

            logger.info("Microservice resumed successfully.")
            print(
                f"Your service was resumed successfully! Project ID: {picked_microservice.project_id}, "
                f"Service ID: {picked_microservice.id}, "
                f"Name: {picked_microservice.microservice_name}, Location: {picked_microservice.project_location}."
            )
        except Exception as e:
            logger.error(f"Failed to resume microservice: {e}")
            raise

    def microservice_insights(
        self,
        user_id: int,
        project_id: int,
        microservice_id: int
    ) -> None:
        """
        Continuously retrieve and display insights for a microservice.
        """
        logger.info("Starting to monitor microservice insights.")
        manager = ActionManager(
            Microservice(
                project_id=project_id,
                status="",
                project_location="",
                license_text="",
                license_file_url="",
                created_by=user_id,
                updated_by=user_id
            ),
            self.agents,
            self.rag_agents,
            self.database_path,
            self.graph_recursion_limit
        )
        manager.microservice_insights(user_id, project_id, microservice_id)

    @staticmethod
    def _prompt_user_for_project_generation(
        manual_prompt: str,
        min_length: int = 0,
        file_option_label: str = "1",
        manual_option_label: str = "2",
    ) -> str:
        """
        Generic method to prompt the user for input, either via a file or manually.
        """
        choice_prompt = "Enter {file_opt} to provide input via file, or {manual_opt} to enter manually: \n"
        while True:
            try:
                input_type = input(choice_prompt.format(
                    file_opt=file_option_label, manual_opt=manual_option_label
                )).strip()
                if input_type == file_option_label:
                    return Action._prompt_for_file_input()
                elif input_type == manual_option_label:
                    return Action._prompt_for_input(manual_prompt, min_length=min_length)
                else:
                    print(f"Invalid choice. Please enter {file_option_label} or {manual_option_label}.")
            except Exception as e:
                logger.exception("Error during user input type selection.")
                raise

    @staticmethod
    def _get_project_details(user_id: int) -> Optional[int]:
        """
        Retrieve and validate project details for the given user.
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
            return next((ms for ms in active_microservices if ms.id == selected_id), None)
        except Exception as e:
            logger.exception("An error occurred while retrieving microservice details.")
            raise

    @staticmethod
    def _get_session_details(user_id: int, project_id: int, microservice_id: int) -> Optional[List[MicroserviceSession]]:
        """
        Retrieve session details for the specified user, project, and microservice.
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
    def _list_items(items: List[Any], display_func, title: str):
        """
        Display a list of items to the user.
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
        """
        while True:
            try:
                user_input = int(input(f"{prompt}: ").strip())
                if validate_func(user_input):
                    logger.info(f"User input accepted: {user_input}")
                    return user_input
                print(error_message)
            except ValueError:
                print("Invalid input. Please enter a valid integer.")
            except Exception as e:
                logger.exception("An error occurred while prompting the user.")
                raise

    @staticmethod
    def _prompt_for_input(prompt_message: str, min_length: int) -> str:
        """
        Prompt the user for input and validate by minimum length.
        """
        while True:
            try:
                user_input = input(f"{prompt_message}: ").strip()
                if len(user_input) >= min_length:
                    logger.debug(f"User provided valid input: {user_input}")
                    return user_input
                print(f"Input too short. Please enter at least {min_length} characters.")
            except Exception as e:
                logger.exception("Error during user input.")
                raise

    @staticmethod
    def _prompt_for_file_input() -> str:
        """
        Prompt the user for a file path, validate extension, existence, and content length.
        """
        while True:
            try:
                file_path = input("Enter the path to your Markdown file (.md): ").strip()
                if not file_path.lower().endswith(".md"):
                    print("Invalid file type. Please provide a Markdown (.md) file.")
                    continue
                if not os.path.exists(file_path):
                    print("File does not exist. Please enter a valid file path.")
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read().strip()
                except UnicodeDecodeError:
                    print("The file contains unsupported characters or is not in a readable text format.")
                    print("Please provide a valid UTF-8 encoded Markdown (.md) file.")
                    logger.error(f"Unsupported characters detected in file: {file_path}")
                    continue
                if len(content) < 20:
                    print("File content is too short. Please provide a file with at least 20 characters.")
                    continue
                logger.debug(f"User provided valid file input from {file_path}")
                return content
            except Exception as e:
                logger.exception("Error during file input processing.")
                raise

    @staticmethod
    def _get_project(project_id: int, user_id: int) -> Optional[Project]:
        """
        Retrieve and validate project details for the specified user.
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
