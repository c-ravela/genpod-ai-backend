from enum import Enum


class TestsGeneratorNodeEnum(str, Enum):
    ENTRY = "entry"
    TEST_CODE_GENERATION = "testcode_generation"
    RUN_COMMANDS = "run_commands"
    WRITE_GENERATED_CODE = "write_code"
    WRITE_SKELETON = "write_skeleton"
    DOWNLOAD_LICENSE = "download_license"
    ADD_LICENSE = "add_license_text"
    UPDATE_STATE = "update_state"
    SKELETON_GENERATION = "skeleton_generation"
    SKELETON_UPDATION = "skeleton_update"
    TEST_CODE_UPDATION = "test_case_updation"
    EXIT = "exit"

    def __str__(self):
        return self.value
