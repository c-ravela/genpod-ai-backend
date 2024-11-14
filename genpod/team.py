from configs.project_config import ProjectAgents, ProjectGraphs
from genpod.architect import ArchitectMember
from genpod.coder import CoderMember
from genpod.member import AgentMember
from genpod.planner import PlannerMember
from genpod.rag import RagMember
from genpod.reviewer import ReviewerMember
from genpod.supervisor import SupervisorMember
from genpod.tests_generator import TestsGeneratorMember


class TeamMembers:
    """
    Manages a team of different agents.
    """

    def __init__(self, agents: ProjectAgents, graphs: ProjectGraphs, persistance_db_path: str, vector_db_collection: str) -> None:
        """
        Initializes the team members with their configurations and state/graph setups.
        """

        self.supervisor = SupervisorMember(agents, graphs, persistance_db_path)
        self.supervisor.set_role(AgentMember.Role.MANAGER)

        self.architect = ArchitectMember(agents, graphs, persistance_db_path)
        self.architect.set_role(AgentMember.Role.LEAD)

        self.coder = CoderMember(agents, graphs, persistance_db_path)
        self.planner = PlannerMember(agents, graphs, persistance_db_path)
        self.rag = RagMember(agents, graphs, persistance_db_path, vector_db_collection)
        self.tests_generator = TestsGeneratorMember(agents, graphs, persistance_db_path)
        self.reviewer = ReviewerMember(agents, graphs, persistance_db_path)
        
    def get_team_members_as_list(self) -> list[AgentMember]:
        """
        Returns a list of all agent members in the team.
        """

        members = []

        for attr_name in dir(self):

            attr_value = getattr(self, attr_name)

            if isinstance(attr_value, AgentMember):
                members.append(attr_value)
                
        return members

    def print_team(self) -> None:
        """
        Prints out the details of all team members.
        """
        import pprint as pp
        members = self.get_team_members_as_list()
        for member in members:
            print("\n")
            pp.pprint(str(member))
            print("\n")
