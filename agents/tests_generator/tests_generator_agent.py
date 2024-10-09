"""Test Coder Agent
"""
import os

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables.base import RunnableSequence
from langchain_openai import ChatOpenAI
from typing_extensions import Literal

from agents.agent.agent import Agent
from agents.tests_generator.tests_generator_state import TestCoderState
from configs.project_config import ProjectAgents
from models.constants import ChatRoles, PStatus, Status
from models.tests_generator_models import (FileFunctionSignatures,
                                           FunctionSkeleton,
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
    entry_node_name: str # The entry point of the graph
    test_code_generation_node_name: str 
    skeleton_generation_node_name: str
    skeleton_updation_node_name: str
    test_code_updation_node_name: str
    segregation_node_name:str
    run_commands_node_name: str
    write_generated_code_node_name: str
    write_skeleton_node_name:str
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
    is_segregated:bool
    is_skeleton_written_to_local:bool
    has_skeleton_been_written_locally: bool
    is_license_file_downloaded: bool
    is_license_text_added_to_files: bool
    hasPendingToolCalls: bool

    last_visited_node: str
    error_message: str
    
    track_add_license_txt: list[str]

    current_code_generation: TestCodeGeneration

    # chains
    test_code_generation_chain: RunnableSequence
    skeleton_generation_chain: RunnableSequence
    
    skeleton_updation_chain: RunnableSequence
    test_code_updation_chain: RunnableSequence

    def __init__(self, llm: ChatOpenAI) -> None:
        """
        """

        super().__init__(
            ProjectAgents.tests_generator.agent_id,
            ProjectAgents.tests_generator.agent_name,
            TestCoderState(),
            TestGeneratorPrompts(),
            llm
        )

        self.entry_node_name = "entry"
        self.test_code_generation_node_name = "testcode_generation"
        self.run_commands_node_name = "run_commands"
        self.write_generated_code_node_name = "write_code"
        self.write_skeleton_node_name="write_skeleton"
        self.download_license_node_name = "download_license"
        self.add_license_node_name = "add_license_text"
        self.update_state_node_name = "update_state"
        self.skeleton_generation_node_name="skeleton_generation"
        self.skeleton_updation_node_name = "skeleton_update"
        self.test_code_updation_node_name = "test_case_updation"
        self.mode = ""

        self.hasError = False
        self.is_code_generated = False
        self.is_skeleton_generated=False

        self.has_command_execution_finished = False
        self.has_code_been_written_locally = False
        self.is_skeleton_written_to_local= False
        self.has_skeleton_been_written_locally=False
        self.is_license_file_downloaded = False
        self.is_license_text_added_to_files = False
        self.hasPendingToolCalls = False

        self.last_visited_node = self.test_code_generation_node_name
        self.error_message = ""

        self.current_code_generation = TestCodeGeneration()

        self.track_add_license_txt = []
        self.test_code_generation_chain = (
            self.prompts.test_generation_prompt
            | self.llm
            | JsonOutputParser()
        )
        self.skeleton_generation_chain = (
            self.prompts.skeleton_generation_prompt
            | self.llm
            | JsonOutputParser()
        )

        self.skeleton_updation_chain = (
            self.prompts.skeleton_generation_for_issue_prompt
            | self.llm
            | JsonOutputParser()
        )

        self.test_code_updation_chain = (
            self.prompts.unit_test_generation_for_issue_prompt
            | self.llm
            | JsonOutputParser()
        )

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
            elif not self.is_skeleton_written_to_local:
                return self.test_code_generation_node_name
        elif self.mode == 'resolving_issues':
            if not self.is_skeleton_generated:
                return self.skeleton_updation_node_name
            elif not self.is_skeleton_written_to_local:
                return self.test_code_updation_node_name

        return self.update_state_node_name
    
    def update_state_skeleton_generation(self,current_sg:FunctionSkeleton)-> None:
        try:
    
            if self.state['functions_skeleton'] is None:
                self.state["functions_skeleton"] = current_sg['skeletons_to_create']
            else:
                state_ifc = current_sg['skeletons_to_create'].copy()

                for key in state_ifc:
                    if key in self.state['functions_skeleton']:
                        del current_sg['skeletons_to_create'][key]
        except Exception as e:
            logger.info("error",e)

    def update_state_test_code_generation(self, current_cg: TestCodeGeneration) -> None:
        """
        """

        if self.state['files_created'] is None:
            self.state['files_created'] = current_cg['files_to_create']
        else:
            new_list = [item for item in current_cg['files_to_create'] if item not in self.state['files_created']]

            self.state['files_created'] += new_list
        
        if self.state['test_code'] is None:
            self.state["test_code"] = current_cg['test_code']
        else:
            state_ifc = current_cg['test_code'].copy()

            for key in state_ifc:
                if key in self.state['test_code']:
                    del current_cg['test_code'][key]   
        if self.state['infile_license_comments'] is None:
            self.state['infile_license_comments'] = current_cg['infile_license_comments']
        else:
            state_ifc = current_cg['infile_license_comments'].copy()

            for key in state_ifc:
                if key in self.state['infile_license_comments']:
                    del current_cg['infile_license_comments'][key]
            
            self.state['infile_license_comments'].update(current_cg['infile_license_comments'])

        if self.state['commands_to_execute'] is None:
            self.state['commands_to_execute'] = current_cg['commands_to_execute']
        else:
            self.state['commands_to_execute'].update(current_cg['commands_to_execute'])

    def entry_node(self, state: TestCoderState) -> TestCoderState:
        """
        This method is the entry point of the Coder agent. It updates the current state 
        with the provided state and sets the mode based on the project status and the status 
        of the current task.

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
        self.is_skeleton_generated=False
        self.has_command_execution_finished = False
        self.has_skeleton_been_written_locally=False
        self.has_code_been_written_locally = False
        self.is_license_file_downloaded = False
        self.is_license_text_added_to_files = False

        self.current_code_generation = TestCodeGeneration()

        return self.state
    
    def test_code_generation_node(self, state: TestCoderState) -> TestCoderState:
        """
        """
        logger.info(f"----{self.agent_name}: Initiating Unit test code Generation----")

        self.update_state(state)
        self.last_visited_node = self.test_code_generation_node_name

        task = self.state['current_planned_task']

        logger.info(f"----{self.agent_name}: Started working on the task: {task.description}.----")
  
        self.add_message((
            ChatRoles.USER,
            f"Started working on the task: {task.description}."
        ))
        
        while(True):
            try:
                llm_response = self.test_code_generation_chain.invoke({
                    "project_name": self.state['project_name'],
                    "project_path": os.path.join(self.state['project_path'], self.state['project_name']),
                    "requirements_document": self.state['requirements_document'],
                    "task": task.description,
                    "error_message": self.error_message,
                    "functions_skeleton": self.state["functions_skeleton"]
                })
                # logger.info("Called llm response is :" ,llm_response)
                # with open('/home/pranay/Desktop/Generatedfiles/latest/new_file_llmtest.txt', 'w') as file:
                #     file.write(str(llm_response))
                self.hasError = False
                self.error_message = ""

                required_keys = ["files_to_create", "test_code", "infile_license_comments", "commands_to_execute"]
                missing_keys = [key for key in required_keys if key not in llm_response]

                if missing_keys:
                    raise KeyError(f"Missing keys: {missing_keys} in the response. Try Again!")

                self.update_state_test_code_generation(llm_response)
                self.current_code_generation["test_code"] = llm_response['test_code']
                self.current_code_generation.files_to_create = llm_response['files_to_create']
                self.current_code_generation['infile_license_comments'] = llm_response['infile_license_comments']
                self.current_code_generation['commands_to_execute'] = llm_response['commands_to_execute']

                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: Test Code Generation completed!"
                ))

                self.is_code_generated = True

                break
            except Exception as e:
                logger.error(f"----{self.agent_name}: Error Occured at code generation: {str(e)}.----")

                self.hasError = True
                self.error_message = f"An error occurred while processing the request: {str(e)}"

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

        logger.info(f"----{self.agent_name}: Started working on the task: {task.description}.----")
  
        self.add_message((
            ChatRoles.USER,
            f"Started working on the task: {task.description}."
        ))

        while(True):
            try:
                llm_response = self.skeleton_generation_chain.invoke({
                    "project_name": self.state['project_name'],
                    "project_path": os.path.join(self.state['project_path'], self.state['project_name']),
                    "requirements_document": self.state['requirements_document'],
                    "task": task.description,
                    "error_message": self.error_message,
                })

                required_keys = ["skeletons_to_create"]
                missing_keys = [key for key in required_keys if key not in llm_response]

                if missing_keys:
                    raise KeyError(f"Missing keys: {missing_keys} in the response. Try Again!")

                self.update_state_skeleton_generation(llm_response)
                self.current_code_generation["functions_skeleton"] = llm_response['skeletons_to_create']
                logger.info("after state",llm_response)
                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: skeleton generation completed!"
                ))

                self.hasError = False
                self.error_message = ""

                self.is_skeleton_generated = True

                break
            except Exception as e:
                logger.error(f"----{self.agent_name}: Error Occured at skeleton generation: {str(e)}.----")

                self.hasError = True
                self.error_message = f"An error occurred while processing the request: {str(e)}"

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

        while(True):
            try:
                llm_response = self.skeleton_updation_chain({
                    'file_content': FS.read_file(planned_issue.file_path),
                    'issue_details': planned_issue.issue_details(),
                    'project_name': self.state['project_name'],
                    "project_path": os.path.join(self.state['project_path'], self.state['project_name']),
                    "requirements_document": self.state['requirements_document'],
                    "error_message": self.error_message,
                })

                validated_response = FileFunctionSignatures(**llm_response)
                self.current_code_generation["functions_skeleton"] = validated_response.function_signatures

                planned_issue.function_signatures = validated_response
                
                self.error_message = ""
                self.state['current_planned_issue'] = planned_issue
                self.is_skeleton_generated = True

                break
            except Exception as e:
                logger.error(f"{self.agent_name}: Error Occured: ===>{type(e)}<=== {e}.----")

                self.error_message = f"An error occurred while processing the request: {e}"

        return self.state

    def test_code_updation_node(self, state: TestCoderState) -> TestCoderState:
        """
        """

        self.state = state
        self.last_visited_node = self.test_code_updation_node_name

        planned_issue = self.state['current_planned_issue']

        while(True):
            try:
                llm_response = self.test_code_updation_chain.invoke({
                    'file_content': FS.read_file(planned_issue.file_path),
                    'issue_details': planned_issue.issue_details(),
                    'project_name': self.state['project_name'],
                    "project_path": os.path.join(self.state['project_path'], self.state['project_name']),
                    "requirements_document": self.state['requirements_document'],
                    "error_message": self.error_message,
                    "functions_skeleton": planned_issue.function_signatures
                })

                required_keys = ["files_to_create", "test_code", "infile_license_comments", "commands_to_execute"]
                missing_keys = [key for key in required_keys if key not in llm_response]

                if missing_keys:
                    raise KeyError(f"Missing keys: {missing_keys} in the response. Try Again!")

                self.update_state_test_code_generation(llm_response)
                self.current_code_generation["test_code"] = llm_response['test_code']
                self.current_code_generation.files_to_create = llm_response['files_to_create']
                self.current_code_generation['infile_license_comments'] = llm_response['infile_license_comments']
                self.current_code_generation['commands_to_execute'] = llm_response['commands_to_execute']

                planned_issue.test_code = llm_response['test_code']

                self.error_message = ""
                self.state['current_planned_issue'] = planned_issue

                break
            except Exception as e:
                logger.error(f"{self.agent_name}: Error Occured: ===>{type(e)}<=== {e}.----")

                self.error_message = f"An error occurred while processing the request: {e}"

        return self.state

    def run_commands_node(self, state: TestCoderState) -> TestCoderState:
        """
        """
        logger.info(f"----{self.agent_name}: Executing the commands ----")
        #updating the state 
        self.update_state(state)
        self.last_visited_node = self.run_commands_node_name
        try:
            for path, command in self.current_code_generation['commands_to_execute'].items():
                
                logger.info(f"----{self.agent_name}: Started executing the command: {command}, at the path: {path}.----")
    
                self.add_message((
                    ChatRoles.USER,
                    f"Started executing the command: {command}, in the path: {path}."
                ))
                execution_result=Shell.execute_command.invoke({
                    "command": command,
                    "repo_path": path
                })
                #if the command is successfully executed, run the next command 
                if execution_result[0]==False:
                    self.add_message((
                    ChatRoles.USER,
                    f"Successfully executed the command: {command}, in the path: {path}. The output of the command execution is {execution_result[1]}"
                ))
                    #if there is any error in the command execution log the error in the error_message and return the state to router by marking the has error as true and 
                    #last visited node as code generation node to generate the code and commands again, with out running the next set of commands.
                elif execution_result[0]==True:
                    
                    self.hasError=True
                    self.last_visited_node = self.code_generation_node_name
                    self.error_message= f"Error Occured while executing the command: {command}, in the path: {path}. The output of the command execution is {execution_result[1]}. This is the dictionary of commands and the paths where the respective command are supposed to be executed you have generated in previous run: {self.current_code_generation['commands_to_execute']}"
                    self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: {self.error_message}"
                ))
                    logger.error(self.error_message)
                    # return {**self.state}
            
            self.has_command_execution_finished = True
        except Exception as e:
            logger.error(f"----{self.agent_name}: Error Occured while executing the commands : {str(e)}.----")

            self.hasError = True
            self.error_message = f"An error occurred while processing the request: {str(e)}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))
        return {**self.state}
    
    def write_skeleton_node(self, state: TestCoderState) -> TestCoderState:
        """
        """

        logger.info(f"----{self.agent_name}: Writing the generated skeleton to the respective files in the specified paths ----")

        self.update_state(state)
        self.last_visited_node = self.write_skeleton_node_name

        try:
            for path, function_skeleton in self.current_code_generation['functions_skeleton'].items():
                
                logger.info(f"----{self.agent_name}: Started writing the skeleton to the file at the path: {path}.----")
    
                self.add_message((
                    ChatRoles.USER,
                    f"Started writing the skeleton to the file in the path: {path}."
                ))
                execution_result=CodeFileWriter.write_generated_skeleton_to_file.invoke({
                    "generated_code": str(function_skeleton),
                    "file_path": path,
                    "generated_project_path": self.state['project_path']
                })

                #if the code successfully stored in the specifies path, write the next code in the file
                if execution_result[0]==False:
                    self.add_message((
                    ChatRoles.USER,
                    f"Successfully executed the command: , in the path: {path}. The output of the command execution is {execution_result[1]}"
                ))
                    
                   
                elif execution_result[0]==True:
                    
                    self.hasError=True
                    self.last_visited_node = self.write_skeleton_node_name
                    self.error_message= f"Error Occured while writing the skeleton in the path: {path}. The output of writing the skeleton to the file is {execution_result[1]}."
                    self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: {self.error_message}"
                ))

            self.has_skeleton_been_written_locally = True
        except Exception as e:
            logger.error(f"----{self.agent_name}: Error Occured while writing the skelton to the respective files : {str(e)}.----")

            self.hasError = True
            self.error_message = f"An error occurred while processing the request: {str(e)}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))

        return self.state
    
    def write_code_node(self, state: TestCoderState) -> TestCoderState:
        """
        """

        logger.info(f"----{self.agent_name}: Writing the generated unit test code to the respective files in the specified paths ----")

        self.update_state(state)
        self.last_visited_node = self.write_generated_code_node_name

        try:
            for path, code in self.current_code_generation['test_code'].items():
                
                logger.info(f"----{self.agent_name}: Started writing the code to the file at the path: {path}.----")
    
                self.add_message((
                    ChatRoles.USER,
                    f"Started writing the code to the file in the path: {path}."
                ))
                execution_result=CodeFileWriter.write_generated_code_to_file.invoke({
                    "generated_code": code,
                    "file_path": path
                })

                #if the code successfully stored in the specifies path, write the next code in the file
                if execution_result[0]==False:
                    self.add_message((
                    ChatRoles.USER,
                    f"Successfully executed the command: , in the path: {path}. The output of the command execution is {execution_result[1]}"
                ))
                    
                    #if there is any error in writing the code to the files log the error in the error_message and return the state to router by marking the has error as true and 
                    #last visited node as code generation node to generate the code and, with out running the next set of writing the files.
                elif execution_result[0]==True:
                    
                    self.last_visited_node = self.test_code_generation_node_name
                    self.error_message= f"Error Occured while writing the code in the path: {path}. The output of writing the code to the file is {execution_result[1]}."
                    self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: {self.error_message}"
                ))
                logger.error(self.error_message)

            self.has_code_been_written_locally = True

            if self.mode == 'test_code_generation':
                self.state['current_planned_task'].task_status = Status.INPROGRESS
                self.state['current_planned_task'].is_test_code_generated = True
            elif self.mode == 'resolving_issues':
                self.state['current_planned_issue'].status = Status.INPROGRESS
                self.state['current_planned_issue'].is_test_code_generated = True
        except Exception as e:
            logger.error(f"----{self.agent_name}: Error Occured while writing the code to the respective files : {str(e)}.----")

            self.hasError = True
            self.error_message = f"An error occurred while processing the request: {str(e)}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))

        return self.state
    