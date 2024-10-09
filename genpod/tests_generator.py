from agents.tests_generator.tests_generator_graph import TestCoderGraph
from agents.tests_generator.tests_generator_state import TestCoderState
from configs.project_config import ProjectAgents
from genpod.member import AgentMember


class TestsGeneratorMember(AgentMember[TestCoderState, TestCoderGraph]):
    """
    """

    def __init__(self, agents: ProjectAgents, persistance_db_path: str):
        """"""

        tests_generator_config = agents.tests_generator
        super().__init__(
            tests_generator_config, 
            TestCoderState, 
            TestCoderGraph(tests_generator_config.llm, persistance_db_path)
        )
