from enum import Enum


class TestsGeneratorMode(str, Enum):
    """Enumeration of operational modes for the tests generator agent.

    Modes include:
        - GENERATING_TEST_CODE: When the agent is actively generating test code.
        - RESOLVING_ISSUES: When the agent is focused on resolving issues or errors.
        - FINISHED: When the process has completed.
    """

    GENERATING_TEST_CODE = "test_code_generation"
    RESOLVING_ISSUES = "resolving_issues"
    FINISHED = "finished"

    def __str__(self) -> str:
        return self.value


class TestsGenerationStage(str, Enum):
    GENERATE_SKELETON = "generate_skeleton"
    SAVE_SKELETON = "save_skeleton"
    GENERATE_TEST_CODE = "generate_test_code"
    SAVE_TEST_CODE = "save_test_code"
    FINISHED = "finished"

    def __str__(self) -> str:
        return self.value


class ResolveIssueStage(str, Enum):
    UPDATE_SKELETON = "update_skeleton"
    SAVE_SKELETON = "save_skeleton"
    UPDATE_TEST_CODE = "update_test_code"
    SAVE_TEST_CODE = "save_test_code"
    FINISHED = "finished"

    def __str__(self) -> str:
        return self.value
