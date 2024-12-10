"""
Test Coder Agent

Agent for generating unit tests, skeletons, and resolving issues in the codebase.
"""

import os
from typing import Any, Dict

from agents.base.base_agent import BaseAgent
from agents.tests_generator.tests_generator_state import TestCoderState
from llms.llm import LLM
from models.constants import ChatRoles, PStatus, Status
from models.tests_generator_models import (FileFunctionSignatures,
                                           TestCodeGeneration)
from prompts.tests_generator_prompts import TestGeneratorPrompts
from tools.code import CodeFileWriter
from tools.file_system import FS
from tools.shell import Shell
from utils.logs.logging_utils import logger


class TestCoderAgent(BaseAgent[TestCoderState, TestGeneratorPrompts]):
    """
    TestCoderAgent handles the generation of unit test cases, function skeletons,
    and issue resolutions using an LLM-driven workflow.
    """
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        llm: LLM
    ) -> None:
        """
        Initializes the TestCoderAgent with required nodes and prompts.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Descriptive name of the agent.
            llm (LLM): Language model for processing requests.
        """
        super().__init__(
            agent_id,
            agent_name,
            TestCoderState(),
            TestGeneratorPrompts(),
            llm
        )

        self.entry_node_name = "entry"
        self.test_code_generation_node_name = "testcode_generation"
        self.run_commands_node_name = "run_commands"
        self.write_generated_code_node_name = "write_code"
        self.write_skeleton_node_name = "write_skeleton"
        self.download_license_node_name = "download_license"
        self.add_license_node_name = "add_license_text"
        self.update_state_node_name = "update_state"
        self.skeleton_generation_node_name = "skeleton_generation"
        self.skeleton_updation_node_name = "skeleton_update"
        self.test_code_updation_node_name = "test_case_updation"

        self.requirements_document = ''

    def add_message(self, message: tuple[ChatRoles, str]) -> None:
        """
        Adds a single message to the messages field in the state.

        Args:
            message (tuple[str, str]): The message to be added.
        """
        if self.state['messages'] is None:
            self.state['messages'] = [message]
        else:
            self.state['messages'] += [message]

    def router(self, state: TestCoderState) -> str:
        """
        Determines the next node based on the current state.

        Args:
            state (TestCoderState): Current state of the agent.

        Returns:
            str: Name of the next node to execute.
        """
        logger.info(f"{self.agent_name}: Routing to the next node based on current state.")
        if state['mode'] == 'test_code_generation':
            if not state['is_skeleton_generated']:
                return self.skeleton_generation_node_name
            if not state['is_skeleton_written_to_local']:
                return self.test_code_generation_node_name
        elif state['mode'] == 'resolving_issues':
            if not state['is_skeleton_generated']:
                return self.skeleton_updation_node_name
            if not state['is_skeleton_written_to_local']:
                return self.test_code_updation_node_name

        return self.update_state_node_name

    def update_state_from_test_data(self, current: Dict[str, Any]) -> None:
        """
        """

        self.state['test_code'] = current['test_code']
        self.state['function_signatures'] = current['functions_signature']

    def entry_node(self, state: TestCoderState) -> TestCoderState:
        """
        Entry node for initializing the agent's workflow.

        Args:
            state (TestCoderState): Current state of the agent.

        Returns:
            TestCoderState: Updated state after initialization.
        """
        logger.info(f"{self.agent_name}: Entry Node Triggered")
        self.state = state
        self.state['last_visited_node'] = self.entry_node_name

        default_state_values = {
            'hasError': False,
            'is_skeleton_written_to_local': False,
            'hasPendingToolCalls': False,
            'error_message': ""
        }
        for key, value in default_state_values.items():
            self.state[key] = BaseAgent.ensure_value(self.state.get(key), value)
            logger.debug(f"{self.agent_name}: {key} set to {self.state[key]}.")
        
        if self.state['project_status'] == PStatus.EXECUTING:
            if self.state['current_planned_task'].task_status == Status.NEW:
                self.state['mode'] = "test_code_generation"
        elif self.state['project_status'] == PStatus.RESOLVING:
            if self.state['current_planned_issue'].status == Status.NEW:
                self.state['mode'] = "resolving_issues"

        self.state['is_code_generated'] = False
        self.state['is_skeleton_generated'] = False
        self.state['has_command_execution_finished'] = False
        self.state['has_skeleton_been_written_locally'] = False

        self.state['current_test_generation'] = {}
        self.requirements_document = (
            f"{state['requirements_document'].directory_structure}\n"
            f"{state['requirements_document'].coding_standards}\n"
            f"{state['requirements_document'].project_license_information}"
        )

        logger.info(f"{self.agent_name}: Entry Node Initialized Successfully.")
        return self.state

    def test_code_generation_node(self, state: TestCoderState) -> TestCoderState:
        """
        Generates unit test cases for the project.

        Args:
            state (TestCoderState): Current state of the agent.

        Returns:
            TestCoderState: Updated state after test code generation.
        """
        logger.info(f"{self.agent_name}: Starting test code generation.")
        self.state = state
        self.state['last_visited_node'] = self.test_code_generation_node_name

        task = self.state['current_planned_task']
        while True:
            try:
                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.test_generation_prompt, 
                    {
                        "project_name": self.state['project_name'],
                        "project_path": os.path.join(
                            self.state['project_path'], 
                            self.state['project_name']
                        ),
                        "requirements_document": self.requirements_document,
                        "task": task.description,
                        "error_message": self.state['error_message'],
                        "functions_skeleton": self.state['current_test_generation']['functions_signature']
                    }, 
                    TestCodeGeneration
                )

                self.state['hasError'] = False
                self.state['error_message'] = ""

                response = llm_output.response
                self.state['current_test_generation']['test_code'] = response.test_code
                self.state['current_test_generation']['infile_license_comments'] = response.infile_license_comments
                self.state['current_test_generation']['commands_to_execute'] = response.commands_to_execute

                self.state['is_code_generated'] = True
                logger.info(f"{self.agent_name}: Test code generation completed.")
                break
            except Exception as e:
                logger.error(f"{self.agent_name}: Error during test code generation: {e}.")
                self.state['hasError'] = True
                self.state['error_message'] = f"Error during test code generation: {e}"

        return self.state

    def skeleton_generation_node(self, state: TestCoderState) -> TestCoderState:
        """
        Generates function skeletons for the project.

        Args:
            state (TestCoderState): Current state of the agent.

        Returns:
            TestCoderState: Updated state after skeleton generation.
        """
        logger.info(f"{self.agent_name}: Starting function skeleton generation.")
        self.state = state
        self.state['last_visited_node'] = self.skeleton_generation_node_name

        task = self.state['current_planned_task']
        while True:
            try:
                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.skeleton_generation_prompt, 
                    {
                        "project_name": self.state['project_name'],
                        "project_path": os.path.join(
                            self.state['project_path'], 
                            self.state['project_name']
                        ),
                        "requirements_document": self.requirements_document,
                        "task": task.description,
                        "error_message": self.state['error_message'],
                    }, 
                    FileFunctionSignatures
                )

                self.state['current_test_generation']['functions_signature'] = llm_output.response.function_signatures
                self.state['hasError'] = False
                self.state['error_message'] = ""
                self.state['is_skeleton_generated'] = True
                logger.info(f"{self.agent_name}: Skeleton generation completed.")
                break
            except Exception as e:
                logger.error(f"{self.agent_name}: Error during skeleton generation: {e}.")
                self.state['hasError'] = True
                self.state['error_message'] = f"Error during skeleton generation: {e}"

        return self.state
  
    def skeleton_updation_node(self, state: TestCoderState) -> TestCoderState:
        """
        Updates the function skeletons for a planned issue.

        Args:
            state (TestCoderState): Current state of the agent.

        Returns:
            TestCoderState: Updated state after skeleton generation for an issue.
        """
        logger.info(f"{self.agent_name}: Initiating skeleton update for planned issue.")
        self.state = state
        self.state['last_visited_node'] = self.skeleton_updation_node_name
        planned_issue = self.state['current_planned_issue']

        while True:
            try:
                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.skeleton_generation_for_issue_prompt, 
                    {
                        'file_content': FS.read_file(planned_issue.file_path),
                        'issue_details': planned_issue.issue_details(),
                        'project_name': self.state['project_name'],
                        "project_path": os.path.join(
                            self.state['project_path'], 
                            self.state['project_name']
                        ),
                        "requirements_document": self.requirements_document,
                        "error_message": self.state['error_message'],
                    }, 
                    FileFunctionSignatures
                )

                validated_response = llm_output.response
                self.state['current_test_generation']['functions_signature'] = validated_response.function_signatures
                planned_issue.function_signatures = validated_response
                self.state['error_message'] = ""
                self.state['current_planned_issue'] = planned_issue
                self.state['is_skeleton_generated'] = True
                logger.info(f"{self.agent_name}: Successfully updated function skeletons for the issue.")
                break
            except Exception as e:
                logger.error(f"{self.agent_name}: Error occurred during skeleton update: {e}")
                self.state['error_message'] = f"An error occurred during skeleton update: {e}"
                self.state['is_skeleton_generated'] = False

        return self.state

    def test_code_updation_node(self, state: TestCoderState) -> TestCoderState:
        """
        Updates the test code for a planned issue.

        Args:
            state (TestCoderState): Current state of the agent.

        Returns:
            TestCoderState: Updated state after test code generation for an issue.
        """
        logger.info(f"{self.agent_name}: Initiating test code update for planned issue.")
        self.state = state
        self.state['last_visited_node'] = self.test_code_updation_node_name
        planned_issue = self.state['current_planned_issue']

        while True:
            try:
                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.unit_test_generation_for_issue_prompt, 
                    {
                        'file_content': FS.read_file(planned_issue.file_path),
                        'issue_details': planned_issue.issue_details(),
                        'project_name': self.state['project_name'],
                        "project_path": os.path.join(
                            self.state['project_path'], 
                            self.state['project_name']
                        ),
                        "requirements_document": self.requirements_document,
                        "error_message": self.state['error_message'],
                        "functions_skeleton": planned_issue.function_signatures
                    }, 
                    TestCodeGeneration
                )

                response = llm_output.response
                self.state['current_test_generation']['test_code'] = response.test_code
                self.state['current_test_generation']['infile_license_comments'] = response.infile_license_comments
                self.state['current_test_generation']['commands_to_execute'] = response.commands_to_execute
                planned_issue.test_code = response.test_code
                self.state['error_message'] = ""
                self.state['current_planned_issue'] = planned_issue
                logger.info(f"{self.agent_name}: Successfully updated test code for the issue.")
                break
            except Exception as e:
                logger.error(f"{self.agent_name}: Error occurred during test code update: {e}")
                self.state['error_message'] = f"An error occurred during test code update: {e}"

        return self.state

    def run_commands_node(self, state: TestCoderState) -> TestCoderState:
        """
        Executes commands generated for the project.

        Args:
            state (TestCoderState): Current state of the agent.

        Returns:
            TestCoderState: Updated state after command execution.
        """
        logger.info(f"{self.agent_name}: Starting command execution.")
        self.state = state
        self.state['last_visited_node'] = self.run_commands_node_name

        try:
            for path, command in self.state['current_test_generation']['commands_to_execute'].items():
                logger.info(f"{self.agent_name}: Executing command `{command}` at `{path}`.")
                execution_result = Shell.execute_command.invoke({
                    "command": command,
                    "repo_path": path
                })

                if execution_result[0]:  # Error occurred
                    error_message = f"Error while executing `{command}` at `{path}`: {execution_result[1]}"
                    logger.error(error_message)
                    self.state['error_message'] = error_message
                    self.state['hasError'] = True
                    self.state['last_visited_node'] = self.run_commands_node_name
                    break
                else:
                    logger.info(f"Command `{command}` executed successfully.")
                    self.state['error_message'] = ""

            self.state['has_command_execution_finished'] = True
        except Exception as e:
            logger.error(f"{self.agent_name}: Error during command execution: {e}")
            self.state['hasError'] = True
            self.state['error_message'] = f"An error occurred during command execution: {e}"

        return self.state
   
    def write_skeleton_node(self, state: TestCoderState) -> TestCoderState:
        """
        Writes the generated function skeletons to the specified files.

        Args:
            state (TestCoderState): Current state of the agent.

        Returns:
            TestCoderState: Updated state after writing function skeletons to files.
        """
        logger.info(f"{self.agent_name}: Writing generated function skeletons to files.")
        self.state = state
        self.state['last_visited_node'] = self.write_skeleton_node_name

        try:
            for path, function_skeleton in self.state['current_test_generation']['functions_signature'].items():             
                logger.info(f"{self.agent_name}: Writing function skeleton to `{path}`.")
  
                execution_result = CodeFileWriter.write_generated_skeleton_to_file.invoke({
                    "generated_code": str(function_skeleton),
                    "file_path": path,
                    "generated_project_path": self.state['project_path']
                })

                if execution_result[0]:  # Error occurred
                    error_message = (
                        f"Error occurred while writing skeleton to `{path}`. "
                        f"Output: {execution_result[1]}"
                    )
                    logger.error(error_message)
                    self.state['error_message'] = error_message
                    self.state['hasError'] = True
                    self.state['last_visited_node'] = self.write_skeleton_node_name
                    break
                else:
                    logger.info(f"Successfully wrote function skeleton to `{path}`.")
                    self.add_message((
                        ChatRoles.USER,
                        f"Function skeleton successfully written to `{path}`."
                    ))

            self.state['has_skeleton_been_written_locally'] = True
            logger.info(f"{self.agent_name}: All function skeletons successfully written.")
        except Exception as e:
            logger.error(f"{self.agent_name}: Error while writing function skeletons: {e}")
            self.state['hasError'] = True
            self.state['error_message'] = f"An error occurred while writing skeletons: {e}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.state['error_message']}"
            ))

        return self.state

    def write_code_node(self, state: TestCoderState) -> TestCoderState:
        """
        Writes generated unit test code to the respective files.

        Args:
            state (TestCoderState): Current state of the agent.

        Returns:
            TestCoderState: Updated state after writing test code to files.
        """
        logger.info(f"{self.agent_name}: Writing generated test cases to files.")
        self.state = state
        self.state['last_visited_node'] = self.write_generated_code_node_name

        try:
            for path, code in self.state['current_test_generation']['test_code'].items():                
                logger.info(f"{self.agent_name}: Writing test code to `{path}`.")
                execution_result = CodeFileWriter.write_generated_code_to_file.invoke({
                    "generated_code": code,
                    "file_path": path
                })

                if execution_result[0]:  # Error occurred
                    error_message = f"Error while writing code to `{path}`: {execution_result[1]}"
                    logger.error(error_message)
                    self.state['error_message'] = error_message
                    self.state['hasError'] = True
                    self.state['last_visited_node'] = self.test_code_generation_node_name
                    break
                else:
                    logger.info(f"Test code successfully written to `{path}`.")
                    self.state['error_message'] = ""

            if self.state['mode'] == 'test_code_generation':
                self.state['current_planned_task'].task_status = Status.INPROGRESS
                self.state['current_planned_task'].is_test_code_generated = True
            elif self.state['mode'] == 'resolving_issues':
                self.state['current_planned_issue'].status = Status.INPROGRESS
                self.state['current_planned_issue'].is_test_code_generated = True
            
            self.update_state_from_test_data(self.state['current_test_generation'])
        except Exception as e:
            logger.error(f"{self.agent_name}: Error while writing test code to files: {e}")
            self.state['hasError'] = True
            self.state['error_message'] = f"An error occurred while writing test code: {e}"

        return self.state
