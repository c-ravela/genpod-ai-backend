from agents.architect import ArchitectAgent
from agents.coder import CoderAgent
from agents.planner import PlannerAgent
from agents.reviewer import ReviewerAgent
from agents.tests_generator import TestsGeneratorAgent
from configs.project_config import AgentRegistry
from core.agent import BaseAgent
from utils.decorators import auto_repr


@auto_repr
class Team:
    """
    Represents a team of agent members for a project, excluding the supervisor.

    The team includes specialized roles such as Architect, Coder, Planner, Tests Generator, 
    and Reviewer. The supervisor, who acts as the team leader, is managed separately and is not 
    considered part of this team.
    """
    def __init__(self, agent_registry: AgentRegistry, database_path: str) -> None:
        """
        Initializes the team members with their configurations and state setups.

        Args:
            agent_registry (AgentRegistry): Configuration details for the project agents.
            database_path (str): Path to the persistence database.
        """
        self.architect = self._create_architect_agent(agent_registry, database_path)
        self.coder = self._create_coder_agent(agent_registry, database_path)
        self.planner = self._create_planner_agent(agent_registry, database_path)
        self.tests_generator = self._create_tests_generator_agent(agent_registry, database_path)
        self.reviewer = self._create_reviewer_agent(agent_registry, database_path)

    def _create_architect_agent(self, agent_registry: AgentRegistry, database_path: str) -> ArchitectAgent:
        architect_config = agent_registry.architect
        return ArchitectAgent(
            id=architect_config.agent_id,
            name=architect_config.agent_name,
            llm=architect_config.llm,
            recursion_limit=architect_config.recursion_limit,
            persistence_db_path=database_path,
            use_rag=architect_config.use_rag,
            description=architect_config.description
        )

    def _create_coder_agent(self, agent_registry: AgentRegistry, database_path: str) -> CoderAgent:
        coder_config = agent_registry.coder
        return CoderAgent(
            id=coder_config.agent_id,
            name=coder_config.agent_name,
            llm=coder_config.llm,
            recursion_limit=coder_config.recursion_limit,
            persistence_db_path=database_path,
            use_rag=coder_config.use_rag,
            description=coder_config.description
        )

    def _create_planner_agent(self, agent_registry: AgentRegistry, database_path: str) -> PlannerAgent:
        planner_config = agent_registry.planner
        return PlannerAgent(
            id=planner_config.agent_id,
            name=planner_config.agent_name,
            llm=planner_config.llm,
            recursion_limit=planner_config.recursion_limit,
            persistence_db_path=database_path,
            use_rag=planner_config.use_rag,
            description=planner_config.description
        )

    def _create_tests_generator_agent(self, agent_registry: AgentRegistry, database_path: str) -> TestsGeneratorAgent:
        tests_generator_config = agent_registry.tests_generator
        return TestsGeneratorAgent(
            id=tests_generator_config.agent_id,
            name=tests_generator_config.agent_name,
            llm=tests_generator_config.llm,
            recursion_limit=tests_generator_config.recursion_limit,
            persistence_db_path=database_path,
            use_rag=tests_generator_config.use_rag,
            description=tests_generator_config.description
        )

    def _create_reviewer_agent(self, agent_registry: AgentRegistry, database_path: str) -> ReviewerAgent:
        reviewer_config = agent_registry.reviewer
        return ReviewerAgent(
            id=reviewer_config.agent_id,
            name=reviewer_config.agent_name,
            llm=reviewer_config.llm,
            recursion_limit=reviewer_config.recursion_limit,
            persistence_db_path=database_path,
            use_rag=reviewer_config.use_rag,
            description=reviewer_config.description
        )

    def get_team_members(self) -> list[BaseAgent]:
        """
        Automatically retrieves all agent members present in the team by introspecting the
        instance attributes. This ensures that any new agent added as an attribute will be included.
    
        Returns:
            list[BaseAgent]: A list containing all team members.
        """
        return [
            attribute
            for attribute in vars(self).values()
            if isinstance(attribute, BaseAgent)
        ]

    def print_team(self) -> None:
        """
        Prints the details of all team members.
        """
        for member in self.get_team_members():
            print("\n" + str(member) + "\n")
