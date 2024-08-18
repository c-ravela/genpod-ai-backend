from genpod.architect import ArchitectMember
from genpod.coder import CoderMember
from genpod.planner import PlannerMember
from genpod.rag import RagMember
from genpod.supervisor import SupervisorMember


class TeamMembers:
    """
    Manages a team of different agents.
    """

    def __init__(self, persistance_db_path: str, vector_db_collection: str) -> None:
        """
        Initializes the team members with their configurations and state/graph setups.
        """

        self.supervisor = SupervisorMember(persistance_db_path)
        self.architect = ArchitectMember(persistance_db_path)
        self.coder = CoderMember(persistance_db_path)
        self.planner = PlannerMember(persistance_db_path)
        self.rag = RagMember(persistance_db_path, vector_db_collection)
        