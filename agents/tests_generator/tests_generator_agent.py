"""Test Coder Agent"""

import os
from typing import Any, Dict, Literal

from agents.agent.agent import Agent
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


class TestCoderAgent(Agent[TestCoderState, TestGeneratorPrompts]):
    """
    """
    # names of the graph node
    entry_node_name: str  # The entry point of the graph
    test_code_generation_node_name: str
    skeleton_generation_node_name: str
    skeleton_updation_node_name: str
    test_code_updation_node_name: str
    segregation_node_name: str
    run_commands_node_name: str
    write_generated_code_node_name: str
    write_skeleton_node_name: str
    download_license_node_name: str
    add_license_node_name: str
    update_state_node_name: str

    mode: Literal['test_code_generation', 'resolving_issues']

    # local state of this class which is not exposed
    # to the graph state
    hasError: bool
    is_code_generated: bool
    is_skeleton_generated: bool
    has_command_execution_finished: bool
    has_code_been_written_locally: bool
    is_code_written_to_local: bool
    is_segregated: bool
    is_skeleton_written_to_local: bool
    has_skeleton_been_written_locally: bool
    is_license_file_downloaded: bool
    is_license_text_added_to_files: bool
    hasPendingToolCalls: bool

    last_visited_node: str
    error_message: str
    requirements_document: str

    current_test_generation: Dict[str, Any]
    state: TestCoderState

    def __init__(self, agent_id: str, agent_name: str, llm: LLM) -> None:
        """
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
        self.mode = ""

        self.hasError = False
        self.is_code_generated = False
        self.is_skeleton_generated = False

        self.has_command_execution_finished = False
        self.has_code_been_written_locally = False
        self.is_skeleton_written_to_local = False
        self.has_skeleton_been_written_locally = False
        self.is_license_file_downloaded = False
        self.is_license_text_added_to_files = False
        self.hasPendingToolCalls = False

        self.last_visited_node = self.test_code_generation_node_name
        self.error_message = ""

        self.current_test_generation = {}

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
        """
        if self.mode == 'test_code_generation':
            if not self.is_skeleton_generated:
                return self.skeleton_generation_node_name
            
            if not self.is_skeleton_written_to_local:
                return self.test_code_generation_node_name
        elif self.mode == 'resolving_issues':
            if not self.is_skeleton_generated:
                return self.skeleton_updation_node_name
            
            if not self.is_skeleton_written_to_local:
                return self.test_code_updation_node_name

        return self.update_state_node_name

    def update_state_from_test_data(self, current: Dict[str, Any]) -> None:
        """
        """

        self.state['test_code'] = current['test_code']
        self.state['function_signatures'] = current['functions_signature']

    def entry_node(self, state: TestCoderState) -> TestCoderState:
        """
        This method is the entry point of the Coder agent. It updates the current state
        with the provided state and sets the mode based on the project status and the 
        status of the current task.

        Args:
            state (TestCoderState): The current state of the coder.

        Returns:
            TestCoderState: The updated state of the coder.
        """

        logger.info(f"----{self.agent_name}: Initiating Graph Entry Point----")
        self.update_state(state)
        self.last_visited_node = self.entry_node_name

        if self.state['project_status'] == PStatus.EXECUTING:
            if self.state['current_planned_task'].task_status == Status.NEW:
                self.mode = "test_code_generation"
        elif self.state['project_status'] == PStatus.RESOLVING:
            if self.state['current_planned_issue'].status == Status.NEW:
                self.mode = "resolving_issues"

        self.is_code_generated = False
        self.is_skeleton_generated = False
        self.has_command_execution_finished = False
        self.has_skeleton_been_written_locally = False
        self.has_code_been_written_locally = False
        self.is_license_file_downloaded = False
        self.is_license_text_added_to_files = False

        self.current_test_generation = {}

        self.requirements_document = (
            f"{state['requirements_document'].directory_structure}\n"
            f"{state['requirements_document'].coding_standards}\n"
            f"{state['requirements_document'].project_license_information}"
        )

        return self.state
   
    def test_code_generation_node(self, state: TestCoderState) -> TestCoderState:
        """
        """
        logger.info(f"----{self.agent_name}: Initiating Unit test code Generation----")

        self.update_state(state)
        self.last_visited_node = self.test_code_generation_node_name

        task = self.state['current_planned_task']

        logger.info(
            f"----{self.agent_name}: Started working on the task: "
            f"{task.description}.----"
        )

        self.add_message((
            ChatRoles.USER,
            f"Started working on the task: {task.description}."
        ))
       
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
                        "error_message": self.error_message,
                        "functions_skeleton": self.current_test_generation['functions_signature']
                    }, 
                    TestCodeGeneration
                )

                self.hasError = False
                self.error_message = ""

                response = llm_output.response
                self.current_test_generation['test_code'] = response.test_code
                self.current_test_generation['infile_license_comments'] = response.infile_license_comments
                self.current_test_generation['commands_to_execute'] = response.commands_to_execute

                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: Test Code Generation completed!"
                ))

                self.is_code_generated = True

                break
            except Exception as e:
                logger.error(f"{self.agent_name}: Error Occured at code generation: {e}.")

                self.hasError = True
                self.error_message = f"An error occurred while processing the request: {e}"

                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: {self.error_message}"
                ))
      
        return self.state

    def skeleton_generation_node(self, state: TestCoderState) -> TestCoderState:
        """
        """
        logger.info(f"----{self.agent_name}: Initiating skeleton Generation----")

        self.update_state(state)
        self.last_visited_node = self.skeleton_generation_node_name

        task = self.state['current_planned_task']

        logger.info(
            f"----{self.agent_name}: Started working on the task: {task.description}.----"
        )

        self.add_message((
            ChatRoles.USER,
            f"Started working on the task: {task.description}."
        ))

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
                        "error_message": self.error_message,
                    }, 
                    FileFunctionSignatures
                )

                self.current_test_generation['functions_signature'] = llm_output.response.function_signatures

                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: skeleton generation completed!"
                ))

                self.hasError = False
                self.error_message = ""

                self.is_skeleton_generated = True

                break
            except Exception as e:
                logger.error(
                    f"----{self.agent_name}: Error Occured at skeleton generation: {e}.----"
                )

                self.hasError = True
                self.error_message = f"An error occurred while processing the request: {e}"

                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: {self.error_message}"
                ))
      
        return self.state
  
    def skeleton_updation_node(self, state: TestCoderState) -> TestCoderState:
        """
        """

        logger.info(f"----{self.agent_name}: Initiating skeleton Generation----")
        self.state = state
        self.last_visited_node = self.skeleton_updation_node_name

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
                        "error_message": self.error_message,
                    }, 
                    FileFunctionSignatures
                )

                validated_response = llm_output.response
                self.current_test_generation['functions_signature'] = validated_response.function_signatures

                planned_issue.function_signatures = validated_response
              
                self.error_message = ""
                self.state['current_planned_issue'] = planned_issue
                self.is_skeleton_generated = True

                break
            except Exception as e:
                logger.error(
                    f"{self.agent_name}: Error Occured: ===>{type(e)}<=== {e}.----"
                )

                self.error_message = f"Error: {e}"

        return self.state

    def test_code_updation_node(self, state: TestCoderState) -> TestCoderState:
        """
        """

        self.state = state
        self.last_visited_node = self.test_code_updation_node_name

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
                        "error_message": self.error_message,
                        "functions_skeleton": planned_issue.function_signatures
                    }, 
                    TestCodeGeneration
                )

                response = llm_output.response
                self.current_test_generation['test_code'] = response.test_code
                self.current_test_generation['infile_license_comments'] = response.infile_license_comments
                self.current_test_generation['commands_to_execute'] = response.commands_to_execute

                planned_issue.test_code = response.test_code

                self.error_message = ""
                self.state['current_planned_issue'] = planned_issue

                break
            except Exception as e:
                logger.error(
                    f"{self.agent_name}: Error Occured: ===>{type(e)}<=== {e}."
                )

                self.error_message = f"Error: {e}"

        return self.state

    def run_commands_node(self, state: TestCoderState) -> TestCoderState:
        """
        """
        logger.info(f"----{self.agent_name}: Executing the commands ----")
        # updating the state
        self.update_state(state)
        self.last_visited_node = self.run_commands_node_name
        try:
            for path, command in self.current_test_generation['commands_to_execute'].items():
              
                logger.info(
                    f"----{self.agent_name}: Started executing the command: "
                    f"{command}, at the path: {path}.----"
                )

                self.add_message((
                    ChatRoles.USER,
                    f"Started executing the command: {command}, in the path: {path}."
                ))
                execution_result = Shell.execute_command.invoke({
                    "command": command,
                    "repo_path": path
                })
                #if the command is successfully executed, run the next command
                if execution_result[0] is False:
                    self.add_message((
                        ChatRoles.USER,
                        f"Successfully executed the command: {command}, in the path: {path}."
                        f"The output of the command execution is {execution_result[1]}"
                    ))

                # if there is any error in the command execution log the error in the error_message 
                # and return the state to router by marking the has error as true and last visited 
                # node as code generation node to generate the code and commands again, with out 
                # running the next set of commands.
                elif execution_result[0] is True:        
                    self.hasError = True
                    self.last_visited_node = self.run_commands_node_name
                    self.error_message = (
                        f"Error Occured while executing the command: {command}, in the path: {path}. "
                        f"The output of the command execution is {execution_result[1]}. "
                    )

                    self.add_message((
                        ChatRoles.USER,
                        f"{self.agent_name}: {self.error_message}"
                    ))
                    logger.error(self.error_message)

            self.has_command_execution_finished = True
        except Exception as e:
            logger.error(f"{self.agent_name}: Error Occured while executing the commands : {e}.")

            self.hasError = True
            self.error_message = f"An error occurred while processing the request: {e}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))
        return self.state
   
    def write_skeleton_node(self, state: TestCoderState) -> TestCoderState:
        """
        """

        logger.info(f"{self.agent_name}: Writing the generated function signatures")

        self.update_state(state)
        self.last_visited_node = self.write_skeleton_node_name

        try:
            for path, function_skeleton in self.current_test_generation['functions_signature'].items():
              
                logger.info(f"{self.agent_name}: Started writing the skeleton to the file at the path: {path}.")
  
                self.add_message((
                    ChatRoles.USER,
                    f"Started writing the skeleton to the file in the path: {path}."
                ))
                execution_result = CodeFileWriter.write_generated_skeleton_to_file.invoke({
                    "generated_code": str(function_skeleton),
                    "file_path": path,
                    "generated_project_path": self.state['project_path']
                })

                # if the code successfully stored in the specifies path, write the next code in the file
                if execution_result[0] is False:
                    self.add_message((
                        ChatRoles.USER,
                        f"Successfully executed the command: , in the path: {path}. The output of the command execution is {execution_result[1]}"
                    ))         
                elif execution_result[0] is True:
                    self.hasError = True
                    self.last_visited_node = self.write_skeleton_node_name
                    self.error_message = (
                        f"Error Occured while writing the skeleton in the path: {path}." 
                        f"The output of writing the skeleton to the file is {execution_result[1]}."
                    )

            self.has_skeleton_been_written_locally = True
        except Exception as e:
            logger.error(f"{self.agent_name}: Error Occured while writing the skeleton to the respective files : {e}.")

            self.hasError = True
            self.error_message = f"An error occurred while processing the request: {e}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))

        return self.state
   
    def write_code_node(self, state: TestCoderState) -> TestCoderState:
        """
        """

        logger.info(f"{self.agent_name}: Writing generated unit test cases")

        self.update_state(state)
        self.last_visited_node = self.write_generated_code_node_name

        try:
            for path, code in self.current_test_generation['test_code'].items():                
                logger.info(f"{self.agent_name}: Started writing the code to the file at the path: {path}.")
  
                self.add_message((
                    ChatRoles.USER,
                    f"Started writing the code to the file in the path: {path}."
                ))
                execution_result = CodeFileWriter.write_generated_code_to_file.invoke({
                    "generated_code": code,
                    "file_path": path
                })

                # if the code successfully stored in the specifies path, write the next code in the file
                if execution_result[0] is False:
                    self.add_message((
                        ChatRoles.USER,
                        f"Successfully executed the command: , in the path: {path}. The output of the command execution is {execution_result[1]}"
                    ))  
                # if there is any error in writing the code to the files log the error 
                # in the error_message and return the state to router by marking the 
                # has error as true and last visited node as code generation node to generate
                # the code and, with out running the next set of writing the files.
                elif execution_result[0] is True:
                   
                    self.last_visited_node = self.test_code_generation_node_name
                    self.error_message = (
                        f"Error Occured while writing the code in the path: {path}."
                        "The output of writing the code to the file is {execution_result[1]}."
                    )

            self.has_code_been_written_locally = True

            if self.mode == 'test_code_generation':
                self.state['current_planned_task'].task_status = Status.INPROGRESS
                self.state['current_planned_task'].is_test_code_generated = True
            elif self.mode == 'resolving_issues':
                self.state['current_planned_issue'].status = Status.INPROGRESS
                self.state['current_planned_issue'].is_test_code_generated = True
            
            self.update_state_from_test_data(self.current_test_generation)
        except Exception as e:
            logger.error(
                f"{self.agent_name}: Error Occured while writing the code to the respective files : {e}"
            )

            self.hasError = True
            self.error_message = f"An error occurred while processing the request: {e}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))

        return self.state
 