"""Coder Agent
"""
import os

from agents.base.base_agent import BaseAgent
from agents.coder.coder_state import CoderState
from llms.llm import LLM
from models.coder_models import CodeGenerationPlan
from models.constants import ChatRoles, PStatus, Status
from prompts.coder_prompts import CoderPrompts
from tools.code import CodeFileWriter
from tools.file_system import FS
from tools.license import License
from tools.shell import Shell
from utils.logs.logging_utils import logger


class CoderAgent(BaseAgent[CoderState, CoderPrompts]):
    """
    CoderAgent Class

    This class represents an agent responsible for handling coding tasks, 
    generating code, resolving issues, and managing associated workflows.
    """

    def __init__(self, agent_id: str, agent_name: str, llm: LLM) -> None:
        """
        Initializes the CoderAgent with a unique ID, name, and an associated LLM.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Name of the agent.
            llm (LLM): The language learning model used by the agent.
        """
        logger.info(f"Initializing CoderAgent with ID: {agent_id} and Name: {agent_name}")
        super().__init__(
            agent_id,
            agent_name,
            CoderState(),
            CoderPrompts(),
            llm
        )

        self.entry_node_name = "entry"
        self.code_generation_node_name = "code_generation"
        self.general_task_node_name = "general_task"
        self.resolve_issue_node_name = "resolve_issue"
        self.run_commands_node_name = "run_commands"
        self.write_generated_code_node_name = "write_code"
        self.download_license_node_name = "download_license"
        self.add_license_node_name = "add_license_text"
        self.agent_response_node_name = "agent_response"
        self.update_state_node_name = "state_update"

        self.requirements_document = ""
        self.current_code_generation_plan_list = []
        logger.debug("CoderAgent initialization complete.")

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
        logger.debug(f"Added message: {message}")

    def router(self, state: CoderState) -> str:
        """
        Determines the next node in the workflow based on the current state.

        Args:
            state (CoderState): The current state of the coder.

        Returns:
            str: The name of the next node.
        """
        logger.info(f"{self.agent_name}: Routing based on the current state.")
        if state['mode'] == "code_generation":
            if not state['is_code_generated']:
                return self.code_generation_node_name
        elif state['mode'] == "general_task":
            if not state['is_code_generated']:
                return self.general_task_node_name
        elif state['mode'] == "resolving_issues":
            if not state['is_code_generated']:
                return self.resolve_issue_node_name

        if not state['is_license_file_downloaded']:
            return self.download_license_node_name
        else:
            return self.agent_response_node_name

    def entry_node(self, state: CoderState) -> CoderState:
        """
        Entry point of the CoderAgent. Initializes state and determines mode.

        Args:
            state (CoderState): The current state of the coder.

        Returns:
            CoderState: The updated state.
        """
        logger.info(f"{self.agent_name}: Entering entry node.")
        self.state = state
        self.state['last_visited_node'] = self.entry_node_name

        default_state_values = {
            'is_license_file_downloaded': False,
            'error_message': "",
        }
        for key, value in default_state_values.items():
            self.state[key] = BaseAgent.ensure_value(self.state.get(key), value)
            logger.debug(f"{self.agent_name}: {key} set to {self.state[key]}.")
        
        if self.state['project_status'] == PStatus.EXECUTING:
            if self.state['current_planned_task'].task_status == Status.NEW:
                if self.state['current_planned_task'].is_function_generation_required:
                    self.state['mode'] = "code_generation"
                else:
                    self.state['mode'] = "general_task"    
        elif self.state['project_status'] == PStatus.RESOLVING:
            if self.state['current_planned_issue'].status == Status.NEW:
                self.state['mode'] = "resolving_issues"

        self.state['is_code_generated'] = False
        self.state['has_command_execution_finished'] = False
        self.state['has_code_been_written_locally'] = False
        self.state['is_license_text_added_to_files'] = False
        self.state['hasPendingToolCalls'] = False
        self.requirements_document = (
            f"{state['requirements_document'].directory_structure}\n"
            f"{state['requirements_document'].coding_standards}\n"
            f"{state['requirements_document'].project_license_information}"
        )

        self.current_code_generation_plan_list = []
        logger.info(f"{self.agent_name}: Entry node setup complete.")
        return self.state
    
    def general_task_node(self, state: CoderState) -> CoderState:
        """
        Handles general task generation for the current task.

        Args:
            state (CoderState): The current state of the coder.

        Returns:
            CoderState: The updated state.
        """
        logger.info(f"{self.agent_name}: Starting general task generation for Task ID: {state['current_planned_task'].task_id}")
        self.state = state
        self.state['last_visited_node'] = self.general_task_node_name

        task = self.state["current_planned_task"]
        logger.info(f"{self.agent_name}: Working on task: {task.description}")

        self.add_message((
            ChatRoles.USER,
            f"Started working on the task: {task.description}."
        ))

        # TODO: Multiple files can be generated during this phase. Need to change logic to only 
        # generate single file at a time.
        while True:
            try:
                llm_output = self.llm.invoke_with_pydantic_model(self.prompts.code_generation_prompt, {
                    "project_name": self.state['project_name'],
                    "project_path": os.path.join(self.state['project_path'], self.state['project_name']),
                    "requirements_document": self.requirements_document,
                    "error_message": self.state['error_message'],
                    "task": task.description,
                    "functions_skeleton": "no function sekeletons available for this task.",
                    "unit_test_cases": "no unit test cases available for this task."
                }, CodeGenerationPlan)

                cleaned_response = llm_output.response
                self.current_code_generation_plan_list.append(cleaned_response)

                self.state['error_message'] = ""
                logger.info(f"{self.agent_name}: General task generation completed successfully.")
                break # while loop exit
            except Exception as e:
                logger.error(f"{self.agent_name}: Error during general task generation: {type(e).__name__}: {e}")
                self.state['error_message'] = str(e)
                self.add_message((ChatRoles.USER, f"{self.agent_name}: {self.state['error_message']}"))
        
        self.add_message((ChatRoles.USER, f"{self.agent_name}: Code generation completed!"))
        self.state['is_code_generated'] = True
        return self.state

    def code_generation_node(self, state: CoderState) -> CoderState:
        """
        Handles code generation for the specified task using provided skeletons and test cases.

        Args:
            state (CoderState): The current state of the coder.

        Returns:
            CoderState: The updated state.
        """
        logger.info(f"{self.agent_name}: Initiating code generation for Task ID: {state['current_planned_task'].task_id}")
        self.state = state
        self.state['last_visited_node'] = self.code_generation_node_name


        task = self.state["current_planned_task"]
        logger.info(f"{self.agent_name}: Working on task: {task.description}")

        self.add_message((
            ChatRoles.USER,
            f"Started working on the task: {task.description}."
        ))
        
        # TODO: Need to re define the data structure being used for `functions_skeleton`
        for file_path, function_skeleton in self.state['functions_skeleton'].items():
            logger.info(f"{self.agent_name}: Generating code for file: {file_path}")
            while True:

                try:
                    llm_output = self.llm.invoke_with_pydantic_model(self.prompts.code_generation_prompt, {
                        "project_name": self.state['project_name'],
                        "project_path": os.path.join(self.state['project_path'], self.state['project_name']),
                        "requirements_document": self.requirements_document,
                        "error_message": self.state['error_message'],
                        "task": task.description,
                        "functions_skeleton": {file_path: function_skeleton},
                        "unit_test_cases": self.state['test_code']
                    }, CodeGenerationPlan)

                    cleaned_response = llm_output.response
                    self.current_code_generation_plan_list.append(cleaned_response)
                    self.state['error_message'] = ""
                    logger.info(f"{self.agent_name}: Code generation for file '{file_path}' completed successfully.")
                    break # while loop exit
                except Exception as e:
                    logger.error(f"{self.agent_name}: Error during code generation for file '{file_path}': {type(e).__name__}: {e}")
                    self.state['error_message'] = str(e)
                    self.add_message((ChatRoles.USER, f"{self.agent_name}: {self.state['error_message']}"))

        self.add_message((ChatRoles.USER, f"{self.agent_name}: Code generation completed!"))
        self.state['is_code_generated'] = True

        return self.state

    def resolve_issue_node(self, state: CoderState) -> CoderState:
        """
        Resolves issues by generating fixes and updating the state.

        Args:
            state (CoderState): The current state of the coder.

        Returns:
            CoderState: The updated state.
        """
        logger.info(f"{self.agent_name}: Initiating issue resolution for Issue ID: {state['current_planned_issue'].id}")

        self.state = state
        self.state['last_visited_node'] = self.resolve_issue_node_name

        planned_issue = self.state['current_planned_issue']
        logger.info(f"{self.agent_name}: Working on issue: {planned_issue.description}")
        self.add_message((ChatRoles.USER, f"Started working on the issue: {planned_issue.description}."))

        while True:
            try:
                llm_output = self.llm.invoke_with_pydantic_model(self.prompts.issue_resolution_prompt, {
                    "project_name": self.state['project_name'],
                    "project_path": os.path.join(self.state['project_path'], self.state['project_name']),
                    "error_message": self.state['error_message'],
                    "issue": (
                        f"Issue Detected:\n"
                        f"-------------------------\n"
                        f"{planned_issue.issue_details()}\n"
                        f"Please review and address this issue promptly."
                    ),
                    "file_path": planned_issue.file_path,
                    "file_content": FS.read_file(planned_issue.file_path),
                    'function_signatures': planned_issue.function_signatures,
                    "unit_test_code": planned_issue.test_code
                }, CodeGenerationPlan)

                cleaned_response = llm_output.response
                self.current_code_generation_plan_list.append(cleaned_response)

                self.state['error_message'] = ""
                
                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: Issue Resolution completed!"
                ))
                self.state['is_code_generated'] = True
                logger.info(f"{self.agent_name}: Issue resolution for Issue ID '{planned_issue.id}' completed successfully.")
                break # while loop exit
            except FileNotFoundError as ffe:
                logger.error(f"{self.agent_name}: File not found during issue resolution: {ffe}")
                self.state['error_message'] = str(ffe)
                self.add_message((ChatRoles.USER, f"{self.agent_name}: {self.state['error_message']}"))
            except Exception as e:
                logger.error(f"{self.agent_name}: Error during issue resolution: {type(e).__name__}: {e}")
                self.state['error_message'] = str(e)
                self.add_message((ChatRoles.USER, f"{self.agent_name}: {self.state['error_message']}"))
                
        return self.state

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
                    self.add_message((
                        ChatRoles.USER,
                        f"{self.agent_name}: {self.state['error_message']}"
                    ))

                    return self.state
            
            self.state['has_command_execution_finished'] = True
            logger.info(f"{self.agent_name}: All commands executed successfully.")
        except Exception as e:
            logger.error(f"{self.agent_name}: Error during command execution: {type(e).__name__}: {e}")
            self.state['error_message'] = str(e)
            self.add_message((ChatRoles.USER, f"{self.agent_name}: {self.state['error_message']}"))

        return self.state
    
    def write_code_node(self, state: CoderState) -> CoderState:
        """
        Writes generated code to specified files in the appropriate paths.

        Args:
            state (CoderState): The current state of the coder.

        Returns:
            CoderState: The updated state.
        """

        logger.info(f"{self.agent_name}: Writing generated code to files.")
        self.state = state
        self.state['last_visited_node'] = self.write_generated_code_node_name


        try:
            for generation_plan in self.current_code_generation_plan_list:
                for file_path, file_content in generation_plan.file.items():
                    logger.info(f"{self.agent_name}: Writing code to file at path: {file_path}.")

                    tool_execution_result = CodeFileWriter.write_generated_code_to_file.invoke(
                        {
                            "generated_code": file_content.file_code,
                            "file_path": file_path
                        }
                    )

                    # if no errors
                    if not tool_execution_result[0]:
                        logger.info(f"{self.agent_name}: Successfully wrote code to '{file_path}'. Output: {tool_execution_result[1]}")
                        self.add_message((ChatRoles.USER, f"Successfully wrote code to file '{file_path}'."))
                    else:
                        logger.error(f"{self.agent_name}: Error writing code to '{file_path}'. Output: {tool_execution_result[1]}")
                        raise Exception(tool_execution_result[1])
            
            self.state['has_code_been_written_locally'] = True
            logger.info(f"{self.agent_name}: All files written successfully.")
        except Exception as e:
            logger.error(f"{self.agent_name}: Error during code writing: {e}")
            self.state['error_message'] = f"An error occurred while writing code: {e}"
            self.add_message((ChatRoles.USER, f"{self.agent_name}: {self.state['error_message']}"))

        return self.state

    def add_license_text_node(self, state: CoderState) -> CoderState:
        """
        Adds license and copyright information to the generated files.

        Args:
            state (CoderState): The current state of the coder.

        Returns:
            CoderState: The updated state.
        """
        logger.info(f"{self.agent_name}: Adding license text to files.")
        self.state = state
        
        try:
            for generation_plan in self.current_code_generation_plan_list:
                for file_path, file_content in generation_plan.file.items():
                
                    file_extension = os.path.splitext(file_path)[1]

                    if not file_extension:
                        logger.debug(f"{self.agent_name}: Skipping file '{file_path}' due to missing extension.")
                        continue
                
                    file_comment = file_content.license_comments.get(file_extension, "")
                    if file_comment:
                        logger.info(f"{self.agent_name}: Adding license text to file '{file_path}'.")
                        with open(file_path, 'r') as file:
                            content = file.read()

                        with open(file_path, 'w') as file:
                            file.write(f"{file_comment}\n\n{content}")

            self.state['is_license_text_added_to_files'] = True
            logger.info(f"{self.agent_name}: License text added to all applicable files.")
        except Exception as e:
            logger.error(f"{self.agent_name}: Error while adding license text: {e}")
            self.state['error_message'] = f"An error occurred while adding license text: {e}"
            self.add_message((ChatRoles.USER, f"{self.agent_name}: {self.state['error_message']}"))

        return self.state
        
    def download_license_node(self, state: CoderState) -> CoderState:
        """
        Downloads the license file from the provided URL and saves it locally.

        Args:
            state (CoderState): The current state of the coder.

        Returns:
            CoderState: The updated state.
        """
        logger.info(f"{self.agent_name}: Downloading license file.")
        self.state = state
        self.state['last_visited_node'] = self.download_license_node_name
        try:
            license_download_result=License.download_license_file.invoke({
                "url": self.state["license_url"], 
                "file_path": os.path.join(self.state["project_path"], self.state["project_name"], "license")
            })

            self.add_message((ChatRoles.USER, f"Downloaded license from {self.state['license_url']}."))
            self.state['is_license_file_downloaded'] = True
            logger.info(f"{self.agent_name}: License file downloaded successfully.")
        except Exception as e:
            logger.error(f"{self.agent_name}: Error during license download: {e}")
            self.state['error_message'] = f"An error occurred while downloading the license: {e}"
            self.add_message((ChatRoles.USER, f"{self.agent_name}: {self.state['error_message']}"))

        return self.state

    def agent_response_node(self, state: CoderState) -> CoderState:
        """
        Prepares a response based on the current project and task status.

        Args:
            state (CoderState): The current state of the coder.

        Returns:
            CoderState: The updated state.
        """
        logger.info(f"{self.agent_name}: Preparing response.")
        self.state = state

        if self.state['project_status'] == PStatus.EXECUTING:
            if (
                self.state['is_code_generated'] and
                self.state['has_code_been_written_locally'] and
                self.state['is_license_text_added_to_files']
            ):
                self.state['current_planned_task'].is_code_generated = True
                self.state['current_planned_task'].task_status = Status.DONE
                self.state["code_generation_plan_list"] = self.current_code_generation_plan_list
                logger.info(f"{self.agent_name}: Task marked as DONE.")
            else:
                self.state['current_planned_task'].task_status = Status.ABANDONED
                logger.warning(f"{self.agent_name}: Task marked as ABANDONED due to incomplete steps.")
        elif self.state['project_status'] == PStatus.RESOLVING:
            if (
                self.state['is_code_generated'] and
                self.state['has_code_been_written_locally'] and
                self.state['is_license_text_added_to_files']
            ):
                self.state['current_planned_issue'].status = Status.DONE
                self.state["code_generation_plan_list"] = self.current_code_generation_plan_list
                logger.info(f"{self.agent_name}: Issue marked as DONE.")
            else: 
                self.state['current_planned_issue'].status = Status.ABANDONED
                logger.warning(f"{self.agent_name}: Issue marked as ABANDONED due to incomplete steps.")
        return self.state
