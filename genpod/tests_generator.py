from agents.tests_generator.tests_generator_graph import TestCoderGraph
from agents.tests_generator.tests_generator_state import TestCoderState
from configs.project_config import ProjectAgents, ProjectGraphs
from genpod.member import AgentMember


class TestsGeneratorMember(AgentMember[TestCoderState, TestCoderGraph]):
    """
    """

    def __init__(self, agents: ProjectAgents, graphs: ProjectGraphs, persistance_db_path: str):
        """"""

        tests_generator_config = agents.tests_generator
        tstg_grph = graphs.tests_generator
        super().__init__(
            tests_generator_config, 
            TestCoderState, 
            TestCoderGraph(
                tstg_grph.graph_id,
                tstg_grph.graph_name,
                tests_generator_config.agent_id,
                tests_generator_config.agent_name,
                tests_generator_config.llm, 
                persistance_db_path
            )
        )
