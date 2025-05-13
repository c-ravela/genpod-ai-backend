"""Coder Agent
"""
import os

from agents.coder._internal.coder_mode_enum import (CodeGenerationStage,
                                                    CoderMode,
                                                    ResolveIssueStage)
from agents.coder._internal.coder_node_enum import CoderNodeEnum
from agents.coder._internal.coder_prompt import CoderPrompts
from agents.coder._internal.coder_state import CoderOutput, CoderState
from core.decorators import (handle_errors_and_reset, record_node,
                             route_on_errors)
from core.workflow import BaseWorkFlow
from llms.llm import LLM
from models.coder_models import CodeGenerationPlan
from models.constants import ChatRoles, PStatus, Status
from tools.code import CodeFileWriter
from tools.file_system import FS
from tools.license import License
from tools.shell import Shell
from utils.logger import logger


class CoderWorkFlow(BaseWorkFlow[CoderPrompts]):
    """
    CoderWorkFlow manages the workflow for code generation and issue resolution.

    This class extends BaseWorkFlow and is responsible for handling prompts,
    managing code generation plans, and maintaining the requirements document.

    Attributes:
        requirements_document (str): Stores the requirements document for the coding task.
        current_code_generation_plan_list (list): Stores the list of code generation plans.
    """

    def __init__(self, agent_id: str, agent_name: str, llm: LLM, use_rag: bool):
        """
        Initializes the CoderWorkFlow instance.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Name of the agent.
            llm (LLM): The large language model used for processing.
            use_rag (bool): Flag indicating whether retrieval-augmented generation (RAG) is used.
        """
        logger.info(f"Initializing CoderWorkFlow with agent_id={agent_id}, agent_name={agent_name}, use_rag={use_rag}")
        super().__init__(agent_id, agent_name, CoderPrompts(use_rag), llm, use_rag)

        self.current_code_generation_plan_list = []

        logger.debug("CoderWorkFlow initialized successfully.")

    @route_on_errors
    def router(self, state: CoderState) -> str:
        """
        Routes the given state to the appropriate coder node based on the current 
        operational mode and mode stage.
        
        Args:
            state (CoderState): The current state of the coder, containing the 
                                operational mode and mode stage.
        
        Returns:
            str: The corresponding coder node enum as a string.
        """
        logger.info(f"Routing state: operational_mode={state.operational_mode}, current_mode_stage={state.current_mode_stage}")
        
        if state.operational_mode == CoderMode.CODE_GENERATION:
            if state.current_mode_stage == CodeGenerationStage.GENERATE_CODE:
                logger.debug("Routing to CODE_GENERATION")
                return str(CoderNodeEnum.CODE_GENERATION)
            elif state.current_mode_stage == CodeGenerationStage.GENERATE_CODE_FROM_SKELETON:
                logger.debug("Routing to CODE_GENERATION_FROM_SKELETON")
                return str(CoderNodeEnum.CODE_GENERATION_FROM_SKELETON)
            elif state.current_mode_stage == CodeGenerationStage.SAVE_CODE:
                logger.debug("Routing to WRITE_GENERATED_CODE")
                return str(CoderNodeEnum.WRITE_GENERATED_CODE)
            elif state.current_mode_stage == CodeGenerationStage.ADD_LICENSE_HEADER:
                logger.debug("Routing to ADD_LICENSE")
                return str(CoderNodeEnum.ADD_LICENSE)
            elif state.current_mode_stage == CodeGenerationStage.DOWNLOAD_LICENSE_FILE:
                logger.debug("Routing to DOWNLOAD_LICENSE")
                return str(CoderNodeEnum.DOWNLOAD_LICENSE)
            elif state.current_mode_stage == CodeGenerationStage.FINISHED:
                logger.debug("Routing to EXIT")
                return str(CoderNodeEnum.EXIT)
            else:
                logger.warning(f"Unhandled CodeGenerationStage: {state.current_mode_stage}")
        
        elif state.operational_mode == CoderMode.ISSUE_RESOLUTION:
            if state.current_mode_stage == ResolveIssueStage.RESOLVE_ISSUE:
                logger.debug("Routing to RESOLVE_ISSUE")
                return str(CoderNodeEnum.RESOLVE_ISSUE)
            elif state.current_mode_stage == ResolveIssueStage.SAVE_CODE:
                logger.debug("Routing to WRITE_GENERATED_CODE")
                return str(CoderNodeEnum.WRITE_GENERATED_CODE)
            elif state.current_mode_stage == ResolveIssueStage.ADD_LICENSE_HEADER:
                logger.debug("Routing to ADD_LICENSE")
                return str(CoderNodeEnum.ADD_LICENSE)
            elif state.current_mode_stage == ResolveIssueStage.FINISHED:
                logger.debug("Routing to EXIT")
                return str(CoderNodeEnum.EXIT)
            else:
                logger.warning(f"Unhandled ResolveIssueStage: {state.current_mode_stage}")

        logger.warning("Unhandled operational mode, defaulting to EXIT")
        return str(CoderNodeEnum.EXIT)

    @record_node(CoderNodeEnum.ENTRY)
    def entry_node(self, state: CoderState) -> CoderState:
        """
        Processes the coder state to update the operational mode and stage based on the project's
        current status, planned tasks, and issues. Additionally, it assembles the requirements document
        and resets the code generation plan list.

        Args:
            state (CoderState): The current state of the coder containing project status, task/issue details,
                                and the requirements document.

        Returns:
            CoderState: The updated state after processing.
        """
        logger.debug("Entering entry_node with state: %s", state)

        if state.project_status == PStatus.EXECUTING:
            if state.current_planned_task.task_status == Status.NEW:
                if state.current_planned_task.is_function_generation_required:
                    state.current_mode_stage = CodeGenerationStage.GENERATE_CODE
                    logger.debug("Task requires function generation; setting mode stage to GENERATE_CODE")
                else:
                    state.current_mode_stage = CodeGenerationStage.GENERATE_CODE_FROM_SKELETON
                    logger.debug("Task does not require function generation; setting mode stage to GENERATE_CODE_FROM_SKELETON")
                state.operational_mode = CoderMode.CODE_GENERATION
                logger.debug("Project status EXECUTING; operational mode set to CODE_GENERATION")
        elif state.project_status == PStatus.RESOLVING:
            if state.current_planned_issue.status == Status.NEW:
                state.operational_mode = CoderMode.ISSUE_RESOLUTION
                state.current_mode_stage = ResolveIssueStage.RESOLVE_ISSUE
                logger.debug("Project status RESOLVING; operational mode set to ISSUE_RESOLUTION with stage RESOLVE_ISSUE")

        self.current_code_generation_plan_list = []
        logger.debug("Reset current code generation plan list.")

        logger.debug("Exiting entry_node with updated state: %s", state)
        return state

    @record_node(CoderNodeEnum.CODE_GENERATION)
    @handle_errors_and_reset
    def generate_code_node(self, state: CoderState) -> CoderState:
        """
        Generates code by invoking the language model using the current task's details.
        The function constructs the necessary prompt parameters, calls the language model,
        and appends the cleaned response to the code generation plan list. Finally, it
        updates the coder state to transition to the SAVE_CODE stage.

        Args:
            state (CoderState): The current state of the coder containing project details,
                                planned task, error messages, and other relevant information.

        Returns:
            CoderState: The updated state after processing the code generation.
        """
        task = state.current_planned_task
        logger.debug("Starting generate_code_node for task: %s", task.description)

        project_path = os.path.join(state.project_directory, state.project_name)
        logger.debug("Constructed project path: %s", project_path)

        prompt_params = {
            "project_name": state.project_name,
            "project_path": project_path,
            "requirements_document": state.requirements_document.to_markdown(),
            "error_message": state.error_message,
            "task": task.description,
            "functions_skeleton": "no function skeletons available for this task.",
            "unit_test_cases": "no unit test cases available for this task."
        }
        logger.debug("Prepared prompt parameters for code generation: %s", prompt_params)

        llm_output = self.invoke_with_pydantic_model(
            self.prompts.code_generation_prompt,
            prompt_params,
            CodeGenerationPlan
        )
        logger.debug("Received LLM output: %s", llm_output)

        cleaned_response = llm_output.response
        logger.debug("Cleaned response from LLM: %s", cleaned_response)

        self.current_code_generation_plan_list.append(cleaned_response)
        logger.debug("Appended cleaned response to code generation plan list. Current list: %s", 
                    self.current_code_generation_plan_list)

        state.current_mode_stage = CodeGenerationStage.SAVE_CODE
        logger.debug("Updated state.current_mode_stage to SAVE_CODE.")

        logger.debug("Exiting generate_code_node with updated state: %s", state)
        return state

    @record_node(CoderNodeEnum.CODE_GENERATION_FROM_SKELETON)
    @handle_errors_and_reset
    def generate_code_from_skeletons_node(self, state: CoderState) -> CoderState:
        """
        Generates code for each function skeleton provided in the state. For each file and its associated 
        function skeleton in the state's functions_skeleton dictionary, this node invokes the language model
        to generate code based on the skeleton and appends the cleaned response to the code generation plan list.
        Finally, the node updates the coder state to transition to the SAVE_CODE stage.

        Args:
            state (CoderState): The current coder state containing project details, error messages, the test code,
                                and a mapping of file paths to function skeletons.

        Returns:
            CoderState: The updated state after processing the code generation from skeletons.
        """
        task = state.current_planned_task
        logger.debug("Starting generate_code_from_skeletons_node for task: %s", task.description)

        project_path = os.path.join(state.project_directory, state.project_name)
        logger.debug("Constructed project path: %s", project_path)

        for file_path, function_skeleton in state.functions_skeleton.items():
            logger.debug("Generating code for file: %s with provided skeleton.", file_path)

            prompt_params = {
                "project_name": state.project_name,
                "project_path": project_path,
                "requirements_document": state.requirements_document.to_markdown(),
                "error_message": state.error_message,
                "task": task.description,
                "functions_skeleton": {file_path: function_skeleton},
                "unit_test_cases": state.test_code
            }
            logger.debug("Prepared prompt parameters: %s", prompt_params)
            
            llm_output = self.invoke_with_pydantic_model(
                self.prompts.code_generation_prompt,
                prompt_params,
                CodeGenerationPlan
            )
            logger.debug("Received LLM output: %s", llm_output)

            cleaned_response = llm_output.response
            logger.debug("Cleaned response from LLM: %s", cleaned_response)

            self.current_code_generation_plan_list.append(cleaned_response)
            logger.debug("Appended cleaned response to code generation plan list. Current list: %s",
                         self.current_code_generation_plan_list)

        state.current_mode_stage = CodeGenerationStage.SAVE_CODE
        logger.debug("Updated state.current_mode_stage to SAVE_CODE.")

        logger.debug("Exiting generate_code_from_skeletons_node with updated state: %s", state)
        return state

    @record_node(CoderNodeEnum.WRITE_GENERATED_CODE)
    @handle_errors_and_reset
    def write_generated_code_node(self, state: CoderState) -> CoderState:
        """
        Writes the generated code to files based on the code generation plan list.

        For each generation plan in the current code generation plan list, this node iterates over the
        file entries and invokes the CodeFileWriter tool to write the generated code to the corresponding
        file path. Successful writes and errors are logged accordingly. Finally, the coder state's mode stage
        is updated to proceed to the next step (adding the license header).

        Args:
            state (CoderState): The current state of the coder, including the code generation plans and the
                                current mode stage.

        Returns:
            CoderState: The updated state after writing the generated code to files.
        """
        logger.debug("Starting write_generated_code_node with %d generation plan(s).", len(self.current_code_generation_plan_list))
    
        for generation_plan in self.current_code_generation_plan_list:
            if not hasattr(generation_plan, 'file') or not isinstance(generation_plan.file, dict):
                logger.warning("Skipping invalid generation plan (missing or invalid 'file' mapping): %s", generation_plan)
                continue

            for file_path, file_content in generation_plan.file.items():
                logger.info("%s: Writing code to file at path: %s.", self.agent_name, file_path)

                tool_execution_result = CodeFileWriter.write_generated_code_to_file.invoke(
                    {
                        "generated_code": file_content.file_code,
                        "file_path": file_path
                    }
                )

                # if no errors
                if not tool_execution_result[0]:
                    logger.info("%s: Successfully wrote code to '%s'. Output: %s", 
                                self.agent_name, file_path, tool_execution_result[1])
                else:
                    logger.error("%s: Error writing code to '%s'. Output: %s", 
                                self.agent_name, file_path, tool_execution_result[1])

        if state.operational_mode == CoderMode.CODE_GENERATION:
            state.current_mode_stage = CodeGenerationStage.ADD_LICENSE_HEADER
            logger.debug("%s: Updated state.current_mode_stage to ADD_LICENSE_HEADER (CODE_GENERATION mode).",
                        self.agent_name)
        elif state.operational_mode == CoderMode.ISSUE_RESOLUTION:
            state.current_mode_stage = ResolveIssueStage.ADD_LICENSE_HEADER
            logger.debug("%s: Updated state.current_mode_stage to ADD_LICENSE_HEADER (ISSUE_RESOLUTION mode).",
                        self.agent_name)
        else:
            logger.warning("%s: Unknown operational mode: %s. Mode stage not updated.",
                        self.agent_name, state.operational_mode)

        logger.debug("%s: Exiting write_generated_code_node with updated state: %s", self.agent_name, state)
        return state

    @record_node(CoderNodeEnum.ADD_LICENSE)
    @handle_errors_and_reset
    def add_license_text_node(self, state: CoderState) -> CoderState:
        """
        Adds license text to generated code files based on their file extension.

        This function iterates over the current code generation plan list and, for each file,
        determines the file extension to retrieve the corresponding license comment. If a valid
        license comment exists, the function prepends it to the file's existing content. Finally,
        the coder state's mode stage is updated based on whether the license file has been downloaded.

        Args:
            state (CoderState): The current coder state containing project details, the status of the
                                license file download, and the code generation plans.

        Returns:
            CoderState: The updated state after adding the license text to the generated files.
        """
        logger.debug("%s: Starting add_license_text_node with %d code generation plan(s).",
                    self.agent_name, len(self.current_code_generation_plan_list))

        for generation_plan in self.current_code_generation_plan_list:
            if not hasattr(generation_plan, 'file') or not isinstance(generation_plan.file, dict):
                logger.warning("Skipping invalid generation plan (missing or invalid 'file' mapping): %s", generation_plan)
                continue

            for file_path, file_content in generation_plan.file.items():
                logger.debug("Processing file: %s", file_path)
            
                file_extension = os.path.splitext(file_path)[1]
                if not file_extension:
                    logger.debug(f"{self.agent_name}: Skipping file '{file_path}' due to missing extension.")
                    continue
            
                file_comment = file_content.license_comments.get(file_extension, "")
                if file_comment:
                    logger.info(f"{self.agent_name}: Adding license text to file '{file_path}'.")
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()

                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(f"{file_comment}\n\n{content}")
                else:
                    logger.debug("%s: No license comment defined for extension '%s' in file '%s'. Skipping license addition.",
                                self.agent_name, file_extension, file_path)

        if state.operational_mode == CoderMode.CODE_GENERATION:
            if not state.is_license_file_downloaded:
                state.current_mode_stage = CodeGenerationStage.DOWNLOAD_LICENSE_FILE
                logger.debug("%s: License file not downloaded. Setting mode stage to DOWNLOAD_LICENSE_FILE.", self.agent_name)
            else:
                state.current_mode_stage = CodeGenerationStage.FINISHED
                logger.debug("%s: License file downloaded. Setting mode stage to FINISHED.", self.agent_name)
        elif state.operational_mode == CoderMode.ISSUE_RESOLUTION:
            state.current_mode_stage = ResolveIssueStage.FINISHED
            logger.debug("%s: Setting mode stage to FINISHED for ISSUE_RESOLUTION.", self.agent_name)

        logger.debug("%s: Exiting add_license_text_node with updated state: %s", self.agent_name, state)
        return state

    @record_node(CoderNodeEnum.DOWNLOAD_LICENSE)
    @handle_errors_and_reset
    def download_license_node(self, state: CoderState) -> CoderState:
        """
        Downloads the license file from the provided URL and updates the coder state.

        This function invokes the License.download_license_file tool to download the license file from 
        the URL specified in the state's license_url, saving it to the project's designated license file path.
        Once the download is attempted, the state is updated to reflect that the license file is downloaded,
        and the mode stage is set to FINISHED.

        Args:
            state (CoderState): The current coder state containing the project directory, project name,
                                and the URL for the license file.

        Returns:
            CoderState: The updated state after attempting the license file download.
        """
        license_file_path = os.path.join(state.project_directory, state.project_name, "license")
        logger.info("%s: Initiating download of license file from URL: %s to path: %s",
                    self.agent_name, state.license_url, license_file_path)
        
        license_download_result = License.download_license_file.invoke({
            "url": state.license_url, 
            "file_path": license_file_path
        })
        logger.debug("%s: License download result: %s", self.agent_name, license_download_result)

        state.is_license_file_downloaded = True
        state.current_mode_stage = CodeGenerationStage.FINISHED
        logger.info("%s: License file downloaded successfully. Mode stage set to FINISHED.", self.agent_name)
        return state

    @record_node(CoderNodeEnum.RESOLVE_ISSUE)
    @handle_errors_and_reset
    def resolve_issue_node(self, state: CoderState) -> CoderState:
        """
        Resolves a detected issue by invoking the language model to generate a code generation plan
        that addresses the issue. If the file is missing or unreadable, abandon the issue instead.
        """
        func_name = "resolve_issue_node"
        planned_issue = state.current_planned_issue
        file_path = planned_issue.file_path

        # 1) Graceful abandon if no file or unreadable
        if not file_path or not os.path.isfile(file_path):
            reason = "missing" if not file_path else "not a valid file"
            planned_issue.status = Status.ABANDONED
            logger.warning(f"[{func_name}] Abandoning issue {planned_issue.id}: {reason} '{file_path}'")
            return state

        try:
            file_content = FS.read_file(file_path)
        except Exception as e:
            planned_issue.status = Status.ABANDONED
            logger.error(f"[{func_name}] Abandoning issue {planned_issue.id} due to read error: {e}")
            return state

        logger.debug(f"[{func_name}] Read file content from: {file_path}")

        # 2) Existing issue‐resolution logic
        project_path = os.path.join(state.project_directory, state.project_name)
        prompt_params = {
            "project_name": state.project_name,
            "project_path": project_path,
            "error_message": state.error_message,
            "issue": (
                f"Issue Detected:\n"
                f"-------------------------\n"
                f"{planned_issue.issue_details()}\n"
                f"Please review and address this issue promptly."
            ),
            "file_path": file_path,
            "file_content": file_content,
            "function_signatures": planned_issue.function_signatures,
            "unit_test_code": planned_issue.test_code
        }
        logger.debug(f"[{func_name}] Prepared prompt parameters for issue resolution: {prompt_params}")

        llm_output = self.invoke_with_pydantic_model(
            self.prompts.issue_resolution_prompt,
            prompt_params,
            CodeGenerationPlan
        )
        logger.debug(f"[{func_name}] Received LLM output: {llm_output}")

        cleaned_response = llm_output.response
        logger.info(f"[{func_name}] Appending cleaned response to code generation plan list.")
        self.current_code_generation_plan_list.append(cleaned_response)

        state.current_mode_stage = ResolveIssueStage.SAVE_CODE
        logger.debug(f"[{func_name}] Updated state.current_mode_stage to SAVE_CODE, state: {state}")
        return state

    @record_node(CoderNodeEnum.EXIT)
    def exit_node(self, state: CoderState) -> CoderOutput:
        """
        Finalizes the workflow by updating the coder state based on the operational mode and current stage.

        For CODE_GENERATION mode:
            - If the current mode stage is FINISHED, marks the current task as DONE and indicates that the code 
            has been generated. The generated code plan list is saved to the state.
            - Otherwise, marks the task as ABANDONED and logs a warning.

        For ISSUE_RESOLUTION mode:
            - If the current mode stage is FINISHED, marks the current planned issue as DONE and saves the code 
            generation plan list.
            - Otherwise, marks the issue as ABANDONED and logs a warning.

        Args:
            state (CoderState): The current coder state containing operational mode, current mode stage, planned task/issue,
                                and other relevant workflow details.

        Returns:
            CoderOutput: The final state output after processing the exit node.
        """
        func_name = "exit_node"
        logger.debug("%s: Entering %s with state: %s", self.agent_name, func_name, state)

        if state.operational_mode == CoderMode.CODE_GENERATION:
            if state.current_mode_stage == CodeGenerationStage.FINISHED:
                state.current_planned_task.is_code_generated = True
                state.current_planned_task.task_status = Status.DONE
                state.code_generation_plan_list = self.current_code_generation_plan_list
                logger.info("%s: Task completed successfully. Marked as DONE.", self.agent_name)
            else:
                state.current_planned_task.task_status = Status.ABANDONED
                logger.warning(f"{self.agent_name}: Task marked as ABANDONED due to incomplete steps.")

        elif state.operational_mode == CoderMode.ISSUE_RESOLUTION:
            if state.current_mode_stage == ResolveIssueStage.FINISHED:
                state.current_planned_issue.is_code_generated = True
                state.current_planned_issue.status = Status.DONE
                state.code_generation_plan_list = self.current_code_generation_plan_list
                logger.info("%s: Issue resolved successfully. Marked as DONE.", self.agent_name)
            else:
                state.current_planned_issue.status = Status.ABANDONED
                logger.warning(f"{self.agent_name}: Issue marked as ABANDONED due to incomplete steps.")
        else:
            logger.error("%s: Unknown operational mode: %s", self.agent_name, state.operational_mode)

        logger.info("Agent '%s': %s - Exiting workflow (exit node).", self.agent_name, func_name)
        logger.debug("%s: Exiting %s with final state: %s", self.agent_name, func_name, state)
        return state

    def run_commands_node(self, state: CoderState) -> CoderState:
        """
        Executes commands for code generation and updates the state.

        Args:
            state (CoderState): The current state of the coder.

        Returns:
            CoderState: The updated state.
        """
        logger.info(f"{self.agent_name}: Executing commands for code generation.")
        self.state = state
        self.state['last_visited_node'] = self.run_commands_node_name


        # TODO: Add logic for command execution. use self.current_code_generation
        # run one command at a time from the dictionary of commands to execute.
        # Need to add error handling prompt for this node.
        # When command execution fails llm need to re try with different commands
        # look into - Shell.execute_command, whitelisted commands for llm to pick

        #executing the commands one by one 
        try:
            for path, command in self.current_code_generation['commands_to_execute'].items():
                logger.info(f"{self.agent_name}: Executing command '{command}' in path '{path}'.")
    
                execution_result=Shell.execute_command.invoke({
                    "command": command,
                    "repo_path": path
                })

                if not execution_result[0]:
                    logger.info(f"{self.agent_name}: Command '{command}' executed successfully in path '{path}'. Output: {execution_result[1]}")
                    self.add_message((ChatRoles.USER, f"Successfully executed the command: {command}, in path: {path}."))
                    #if there is any error in the command execution log the error in the error_message and return the state to router by marking the has error as true and 
                    #last visited node as code generation node to generate the code and commands again, with out running the next set of commands.
                else:
                    logger.error(f"{self.agent_name}: Error executing command '{command}' in path '{path}'. Output: {execution_result[1]}")
                    self.state['last_visited_node'] = self.code_generation_node_name
                    self.state['error_message']= f"Error Occured while executing the command: {command}, in the path: {path}. The output of the command execution is {execution_result[1]}. This is the dictionary of commands and the paths where the respective command are supposed to be executed you have generated in previous run: {self.current_code_generation['commands_to_execute']}"

                    return self.state
            
            self.state['has_command_execution_finished'] = True
            logger.info(f"{self.agent_name}: All commands executed successfully.")
        except Exception as e:
            logger.error(f"{self.agent_name}: Error during command execution: {type(e).__name__}: {e}")
            self.state['error_message'] = str(e)

        return state
