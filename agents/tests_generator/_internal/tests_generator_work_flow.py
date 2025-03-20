import os

from agents.tests_generator._internal.tests_generator_mode_enum import (
    ResolveIssueStage, TestsGenerationStage, TestsGeneratorMode)
from agents.tests_generator._internal.tests_generator_node_enum import \
    TestsGeneratorNodeEnum
from agents.tests_generator._internal.tests_generator_prompt import \
    TestsGeneratorPrompts
from agents.tests_generator._internal.tests_generator_state import (
    TestCoderOutput, TestCoderState)
from core.decorators import (handle_errors_and_reset, record_node,
                             route_on_errors)
from core.workflow import BaseWorkFlow
from llms.llm import LLM
from models.constants import PStatus, Status
from models.tests_generator_models import (FileFunctionSignatures,
                                           TestCodeGeneration)
from tools.code import CodeFileWriter
from tools.file_system import FS
from tools.shell import Shell
from utils.logger import logger


class TestCoderWorkFlow(BaseWorkFlow[TestsGeneratorPrompts]):

    def __init__(self, agent_id: str, agent_name: str, llm: LLM, use_rag = False):
        super().__init__(agent_id, agent_name, TestsGeneratorPrompts(use_rag), llm, use_rag)

    @route_on_errors
    def router(self, state: TestCoderState) -> str:
        """
        Route the current state to the appropriate test generation node based on the operational mode and mode stage.

        Args:
            state (TestCoderState): The current state of the test coder.

        Returns:
            str: The string identifier of the corresponding TestsGeneratorNodeEnum.
        """
        logger.debug("Routing state: operational_mode=%s, current_mode_stage=%s",
                    state.operational_mode, state.current_mode_stage)

        if state.operational_mode == TestsGeneratorMode.GENERATING_TEST_CODE:
            if state.current_mode_stage == TestsGenerationStage.GENERATE_SKELETON:
                return str(TestsGeneratorNodeEnum.SKELETON_GENERATION)
            elif state.current_mode_stage == TestsGenerationStage.SAVE_SKELETON:
                return str(TestsGeneratorNodeEnum.WRITE_SKELETON)
            elif state.current_mode_stage == TestsGenerationStage.GENERATE_TEST_CODE:
                return str(TestsGeneratorNodeEnum.TEST_CODE_GENERATION)
            elif state.current_mode_stage == TestsGenerationStage.SAVE_TEST_CODE:
                return str(TestsGeneratorNodeEnum.WRITE_GENERATED_CODE)
            elif state.current_mode_stage == TestsGenerationStage.FINISHED:
                return str(TestsGeneratorNodeEnum.EXIT)
            else:
                logger.warning("Unexpected Test Generation stage encountered: %s. Defaulting to EXIT node.",
                            state.current_mode_stage)
        elif state.operational_mode == TestsGeneratorMode.RESOLVING_ISSUES:
            if state.current_mode_stage == ResolveIssueStage.UPDATE_SKELETON:
                return str(TestsGeneratorNodeEnum.SKELETON_UPDATION)
            elif state.current_mode_stage == ResolveIssueStage.SAVE_SKELETON:
                return str(TestsGeneratorNodeEnum.WRITE_SKELETON)
            elif state.current_mode_stage == ResolveIssueStage.UPDATE_TEST_CODE:
                return str(TestsGeneratorNodeEnum.TEST_CODE_UPDATION)
            elif state.current_mode_stage == ResolveIssueStage.SAVE_TEST_CODE:
                return str(TestsGeneratorNodeEnum.WRITE_GENERATED_CODE)
            elif state.current_mode_stage == ResolveIssueStage.FINISHED:
                return str(TestsGeneratorNodeEnum.EXIT)
            else:
                logger.warning("Unexpected Resolve Issues stage encountered: %s. Defaulting to EXIT node.",
                            state.current_mode_stage)

        return str(TestsGeneratorNodeEnum.EXIT)

    @record_node(TestsGeneratorNodeEnum.ENTRY)
    def entry_node(self, state: TestCoderState) -> TestCoderState:
        """
        Entry node for initializing the agent's workflow.

        This method initializes the operational mode and mode stage based on the project's status 
        and the status of the current planned task or issue. It also resets the current test generation
        state and updates the requirements document string for further processing.

        Args:
            state (TestCoderState): The current state of the agent.

        Returns:
            TestCoderState: The updated state after initialization.
        """
        logger.debug("Entering entry_node with project_status: %s", state.project_status)

        if state.project_status == PStatus.EXECUTING:
            if state.current_planned_task.task_status == Status.NEW:
                logger.debug(
                    "New task detected in EXECUTING status. "
                    "Setting operational_mode to GENERATING_TEST_CODE and current_mode_stage to SKELETON_GENERATION."
                )
                state.operational_mode = TestsGeneratorMode.GENERATING_TEST_CODE
                state.current_mode_stage = TestsGenerationStage.GENERATE_SKELETON
        elif state.project_status == PStatus.RESOLVING:
            if state.current_planned_issue.status == Status.NEW:
                logger.debug(
                    "New issue detected in RESOLVING status. "
                    "Setting operational_mode to RESOLVING_ISSUES and current_mode_stage to SKELETON_UPDATION."
                )
                state.operational_mode = TestsGeneratorMode.RESOLVING_ISSUES
                state.current_mode_stage = ResolveIssueStage.UPDATE_SKELETON
        else:
            logger.debug("Project status is neither EXECUTING nor RESOLVING. Setting operational_mode to FINISHED.")
            state.operational_mode = TestsGeneratorMode.FINISHED

        state.current_test_generation = {}

        logger.debug("Exiting entry_node with updated state: %s", state)
        return state

    @record_node(TestsGeneratorNodeEnum.SKELETON_GENERATION)
    @handle_errors_and_reset
    def skeleton_generation_node(self, state: TestCoderState) -> TestCoderState:
        """
        Generate the skeleton of the test code using the skeleton generation prompt.

        This node invokes a language model prompt to generate function skeletons based on the provided project
        details, requirements, and task description. The generated function signatures are stored in the state's
        current test generation data, and the mode stage is updated to SAVE_SKELETON.

        Args:
            state (TestCoderState): The current state containing project and task details.

        Returns:
            TestCoderState: The updated state with generated function signatures and updated mode stage.
        """
        logger.debug("Starting skeleton generation for task: %s", state.current_planned_task.description)

        task = state.current_planned_task

        llm_output = self.invoke_with_pydantic_model(
            self.prompts.skeleton_generation_prompt,
            {
                'project_name': state.project_name,
                'project_path': os.path.join(state.project_directory, state.project_name),
                'requirements_document': state.requirements_document.to_markdown(),
                'task': task.description,
                'error_message': state.error_message
            },
            FileFunctionSignatures
        )
        logger.debug("Skeleton generation response received: %s", llm_output.response)

        state.current_test_generation['functions_signature'] = llm_output.response.function_signatures
        state.current_mode_stage = TestsGenerationStage.SAVE_SKELETON

        logger.info("Skeleton generation complete. Updated mode stage to SAVE_SKELETON.")
        return state

    @record_node(TestsGeneratorNodeEnum.WRITE_SKELETON)
    @handle_errors_and_reset
    def write_skeleton_node(self, state: TestCoderState) -> TestCoderState:
        """
        Write the generated function skeletons to their corresponding files.

        This node iterates through each function signature stored in the state's current test generation data,
        writes the corresponding skeleton code to the designated file using CodeFileWriter, and logs the outcome.
        If writing to any file fails, an error is logged; otherwise, a success message is logged.
        Finally, the state's mode stage is updated based on the operational mode:
        - For GENERATING_TEST_CODE, the stage is set to GENERATE_TEST_CODE.
        - For RESOLVING_ISSUES, the stage is set to UPDATE_TEST_CODE.

        Args:
            state (TestCoderState): The current state of the test coder containing generation data and project details.

        Returns:
            TestCoderState: The updated state after attempting to write all skeleton files.
        """
        functions = state.current_test_generation.get('functions_signature', {})
        logger.debug("Starting write_skeleton_node for %d function(s).", len(functions))

        for path, function_skeleton in functions.items():
            logger.debug("Attempting to write skeleton for function at path: %s", path)
        
            execution_result = CodeFileWriter.write_generated_skeleton_to_file.invoke({
                "generated_code": str(function_skeleton),
                "file_path": path,
                "generated_project_path": state.project_directory
            })

            if execution_result[0]:  # Error occurred
                error_message = (
                    f"Error occurred while writing skeleton to `{path}`. "
                    f"Output: {execution_result[1]}"
                )
                logger.error(error_message)
            else:
                logger.info(f"Successfully wrote function skeleton to `{path}`.")

        if state.operational_mode == TestsGeneratorMode.GENERATING_TEST_CODE:
            state.current_mode_stage = TestsGenerationStage.GENERATE_TEST_CODE
            logger.debug("write_skeleton_node completed. Updated current_mode_stage to GENERATE_TEST_CODE.")
        elif state.operational_mode == TestsGeneratorMode.RESOLVING_ISSUES:
            state.current_mode_stage = ResolveIssueStage.UPDATE_TEST_CODE
            logger.debug("write_skeleton_node completed. Updated current_mode_stage to UPDATE_TEST_CODE for RESOLVING_ISSUES.")

        return state

    @record_node(TestsGeneratorNodeEnum.TEST_CODE_GENERATION)
    @handle_errors_and_reset
    def test_code_generation_node(self, state: TestCoderState) -> TestCoderState:
        """
        Generate the test code using a language model prompt.

        This node generates test code based on project details, requirements, and the current task description.
        It invokes a language model with the test generation prompt and updates the state's test generation data
        with the generated test code, inline license comments, and commands to execute. Finally, it sets the mode
        stage to SAVE_TEST_CODE.

        Args:
            state (TestCoderState): The current state of the test coder containing project, task, and error details.

        Returns:
            TestCoderState: The updated state with generated test code information.
        """
        logger.debug("Starting test code generation for task: %s", state.current_planned_task.description)

        task = state.current_planned_task
        project_path = os.path.join(state.project_directory, state.project_name)
        logger.debug("Invoking test generation prompt for project: '%s' at path: '%s'", state.project_name, project_path)

        llm_output = self.invoke_with_pydantic_model(
            self.prompts.test_generation_prompt, 
            {
                'project_name': state.project_name,
                'project_path': project_path,
                'requirements_document': state.requirements_document.to_markdown(),
                'task': task.description,
                'error_message': state.error_message,
                'functions_skeleton': state.current_test_generation['functions_signature']
            }, 
            TestCodeGeneration
        )

        response = llm_output.response
        logger.debug("Received test generation response: %s", response)

        state.current_test_generation['test_code'] = response.test_code
        state.current_test_generation['infile_license_comments'] = response.infile_license_comments
        state.current_test_generation['commands_to_execute'] = response.commands_to_execute
        state.current_mode_stage = TestsGenerationStage.SAVE_TEST_CODE

        logger.info("Test code generation complete. Updated mode stage to SAVE_TEST_CODE.")
        return state

    @record_node(TestsGeneratorNodeEnum.WRITE_GENERATED_CODE)
    @handle_errors_and_reset
    def write_generated_code_node(self, state: TestCoderState) -> TestCoderState:
        """
        Write the generated test code to the corresponding files.

        This node iterates through each file path and its associated generated test code in the state's
        current test generation data. It writes the code to the designated file using CodeFileWriter and logs
        whether the operation succeeded or failed. Based on the operational mode, it updates the state's mode stage:
        - For GENERATING_TEST_CODE, the stage is set to FINISHED.
        - For RESOLVING_ISSUES, the stage is set to FINISHED (using the ResolveIssueStage).
        
        Finally, it updates the state's test_code and function_signatures with the latest generated content.

        Args:
            state (TestCoderState): The current state of the test coder containing generated code and project details.

        Returns:
            TestCoderState: The updated state after attempting to write all generated test code files.
        """
        test_code = state.current_test_generation.get('test_code', {})
        logger.debug("Starting write_generated_code_node. Number of test code files to write: %d", len(test_code))

        for path, code in test_code.items():
            logger.info(f"{self.agent_name}: Writing test code to `{path}`.")
            execution_result = CodeFileWriter.write_generated_code_to_file.invoke({
                "generated_code": code,
                "file_path": path
            })

            if execution_result[0]:  # Error occurred
                error_message = f"Error while writing code to `{path}`: {execution_result[1]}"
                logger.error(error_message)
            else:
                logger.info(f"Test code successfully written to `{path}`.")

        if state.operational_mode == TestsGeneratorMode.GENERATING_TEST_CODE:
            state.current_mode_stage = TestsGenerationStage.FINISHED
            logger.debug("Operational mode GENERATING_TEST_CODE: Set current_mode_stage to FINISHED.")
        elif state.operational_mode == TestsGeneratorMode.RESOLVING_ISSUES:
            state.current_mode_stage = ResolveIssueStage.FINISHED
            logger.debug("Operational mode RESOLVING_ISSUES: Set current_mode_stage to FINISHED.")

        state.test_code = state.current_test_generation.get('test_code', {})
        state.function_signatures = state.current_test_generation.get('functions_signature', {})
        logger.info("write_generated_code_node completed. State updated with test_code and function_signatures.")    
        return state

    @record_node(TestsGeneratorNodeEnum.SKELETON_UPDATION)
    @handle_errors_and_reset
    def skeleton_updation_node(self, state: TestCoderState) -> TestCoderState:
        """
        Update the test code skeleton for a planned issue.

        This node reads the file content from the planned issue's file path, retrieves the issue details, 
        and invokes a language model prompt to generate updated function signatures for the problematic code.
        The generated skeleton is then stored in the state's test generation data and assigned to the planned issue.
        Finally, the node updates the state's mode stage to SAVE_SKELETON for further processing.

        Args:
            state (TestCoderState): The current state containing project and planned issue details.

        Returns:
            TestCoderState: The updated state with new function signatures for the planned issue.
        """
        logger.debug("Starting skeleton updation for issue at file: %s", state.current_planned_issue.file_path)
        
        planned_issue = state.current_planned_issue

        file_content = FS.read_file(planned_issue.file_path)
        logger.debug("Read file content from: %s", planned_issue.file_path)
        params = {
            'file_content': file_content,
            'issue_details': planned_issue.issue_details(),
            'project_name': state.project_name,
            'project_path': os.path.join(state.project_directory, state.project_name),
            'requirements_document': state.requirements_document.to_markdown(),
            'error_message': state.error_message,
        }
        logger.debug("Invoking skeleton generation for issue with parameters: %s", params)
        
        llm_output = self.invoke_with_pydantic_model(
            self.prompts.skeleton_generation_for_issue_prompt, 
            params,
            FileFunctionSignatures
        )

        validated_response = llm_output.response
        logger.debug("Received skeleton updation response: %s", validated_response)

        state.current_test_generation['functions_signature'] = validated_response.function_signatures
        planned_issue.function_signatures = validated_response
        state.current_planned_issue = planned_issue
        state.current_mode_stage = ResolveIssueStage.SAVE_SKELETON
        logger.info("Skeleton updation complete for issue at file: %s. Mode stage set to SAVE_SKELETON.", planned_issue.file_path)
        return state

    @record_node(TestsGeneratorNodeEnum.TEST_CODE_UPDATION)
    @handle_errors_and_reset
    def test_code_updation_node(self, state: TestCoderState) -> TestCoderState:
        """
        Update the test code for a planned issue using a language model prompt.

        This node reads the file content associated with the planned issue, retrieves the issue details,
        and invokes a language model prompt to generate updated test code. The generated test code,
        inline license comments, and commands to execute are then stored in the state's test generation data
        and assigned to the planned issue. Finally, the mode stage is updated to FINISHED, indicating that
        the issue resolution process is complete.

        Args:
            state (TestCoderState): The current state of the test coder containing project and planned issue details.

        Returns:
            TestCoderState: The updated state with new test code details for the planned issue.
        """
        logger.debug("Starting test code updation for issue at file: %s", state.current_planned_issue.file_path)
    
        planned_issue = state.current_planned_issue

        file_content = FS.read_file(planned_issue.file_path)
        logger.debug("Read file content from: %s", planned_issue.file_path)

        params = {
            'file_content': file_content,
            'issue_details': planned_issue.issue_details(),
            'project_name': state.project_name,
            'project_path': os.path.join(state.project_directory, state.project_name),
            'requirements_document': state.requirements_document.to_markdown(),
            'error_message': state.error_message,
            'functions_skeleton': planned_issue.function_signatures
        }
        logger.debug("Invoking unit test generation for issue with parameters: %s", params)

        llm_output = self.invoke_with_pydantic_model(
            self.prompts.unit_test_generation_for_issue_prompt, 
            params, 
            TestCodeGeneration
        )
        
        response = llm_output.response
        logger.debug("Received test code updation response: %s", response)

        state.current_test_generation['test_code'] = response.test_code
        state.current_test_generation['infile_license_comments'] = response.infile_license_comments
        state.current_test_generation['commands_to_execute'] = response.commands_to_execute
        planned_issue.test_code = response.test_code
        state.current_planned_issue = planned_issue
        state.current_mode_stage = ResolveIssueStage.FINISHED

        logger.info("Test code updation complete for issue at file: %s. Mode stage set to FINISHED.", planned_issue.file_path)
        return state

    @record_node(TestsGeneratorNodeEnum.EXIT)
    def exit_node(self, state: TestCoderState) -> TestCoderOutput:
        """
        Finalize the test code generation or updation process and update the status of the planned task or issue.

        Depending on the operational mode, this node sets the task or issue status to INPROGRESS and flags that
        the test code has been generated. This finalizes the current workflow and returns the updated state as output.

        Args:
            state (TestCoderState): The current state of the test coder containing details of the planned task/issue 
                                    and operational mode.

        Returns:
            TestCoderOutput: The final output state with updated task/issue statuses indicating test code generation progress.
        """
        logger.debug("Entering exit_node with operational_mode: %s", state.operational_mode)

        if state.operational_mode == TestsGeneratorMode.GENERATING_TEST_CODE:
            logger.debug("Setting task status to INPROGRESS and marking test code as generated for the planned task.")
            state.current_planned_task.task_status = Status.INPROGRESS
            state.current_planned_task.is_test_code_generated = True
        elif state.operational_mode == TestsGeneratorMode.RESOLVING_ISSUES:
            logger.debug("Setting issue status to INPROGRESS and marking test code as generated for the planned issue.")
            state.current_planned_issue.status = Status.INPROGRESS
            state.current_planned_issue.is_test_code_generated = True
        else:
            logger.warning("Exit node received an unrecognized operational mode: %s", state.operational_mode)

        logger.info("Exiting exit_node with updated state.")
        return state

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
