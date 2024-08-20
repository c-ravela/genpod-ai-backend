"""Test Coder Agent
"""
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables.base import RunnableSequence
from langchain_openai import ChatOpenAI
from typing_extensions import Literal

from agents.tester.state import TestCoderState
from models.constants import ChatRoles, Status
from models.skeleton import FunctionSkeleton
from models.test_generator import TestCodeGeneration
from prompts.skeleton_generator import SkeletonGeneratorPrompts
from prompts.test_generator import TestGeneratorPrompts
from tools.code import CodeFileWriter
from tools.shell import Shell
from utils.logs.logging_utils import logger


class TestCoderAgent:
    """
    """
    agent_name: str # The name of the agent

    # names of the graph node
    entry_node_name: str # The entry point of the graph
    code_generation_node_name: str 
    skeleton_generation_node_name: str
    segregation_node_name:str
    run_commands_node_name: str
    write_generated_code_node_name: str
    write_skeleton_node_name:str
    download_license_node_name: str 
    add_license_node_name: str 
    update_state_node_name: str 

    mode: Literal["test_code_generation"]

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

    state: TestCoderState
    prompts: TestGeneratorPrompts
    # segregation_prompt: SegregatorPrompts
    skeleton_prompt: SkeletonGeneratorPrompts
    current_code_generation: TestCodeGeneration

    llm: ChatOpenAI # This is the language learning model (llm) for the Architect agent. It can be ChatOpenAI model

    # chains
    test_code_generation_chain: RunnableSequence
    skeleton_generation_chain: RunnableSequence
    # task_segregation_chain: RunnableSequence

    def __init__(self, llm: ChatOpenAI) -> None:
        """
        """
        
        self.agent_name = "Test code Programmer"

        self.entry_node_name = "entry"
        self.code_generation_node_name = "testcode_generation"
        self.run_commands_node_name = "run_commands"
        self.write_generated_code_node_name = "write_code"
        self.write_skeleton_node_name="write_skeleton"
        self.download_license_node_name = "download_license"
        self.add_license_node_name = "add_license_text"
        self.update_state_node_name = "state_update"
        self.skeleton_generation_node_name="skeleton_generation"
        # self.segregation_node_name="segregation"

        self.mode = ""

        self.hasError = False
        self.is_code_generated = False
        self.is_skeleton_generated=False
        # self.is_segregated=False
        self.has_command_execution_finished = False
        self.has_code_been_written_locally = False
        self.is_skeleton_written_to_local= False
        self.has_skeleton_been_written_locally=False
        self.is_license_file_downloaded = False
        self.is_license_text_added_to_files = False
        self.hasPendingToolCalls = False

        self.last_visited_node = self.code_generation_node_name
        self.error_message = ""
        
        self.state = TestCoderState()
        self.prompts = TestGeneratorPrompts()
        self.skeleton_prompt= SkeletonGeneratorPrompts()
        # self.segregation_prompt =SegregatorPrompts()


        self.current_code_generation = {}

        self.llm = llm

        self.track_add_license_txt = []
        self.test_code_generation_chain = (
            self.prompts.test_generation_prompt
            | self.llm
            | JsonOutputParser()
        )
        self.skeleton_generation_chain = (
            self.skeleton_prompt.skeleton_generation_prompt
            | self.llm
            | JsonOutputParser()
        )

        # self.segregaion_chain=(
        #     self.segregation_prompt.segregation_prompt
        #     | self.llm
        #     | JsonOutputParser()
        # )

    def add_message(self, message: tuple[str, str]) -> None:
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

        if self.hasError:
            return self.last_visited_node
        elif self.mode == "test_code_generation":
            if not self.is_skeleton_generated:
                return self.skeleton_generation_node_name
            elif not self.has_skeleton_been_written_locally:
                return self.write_skeleton_node_name
            elif not self.is_code_generated:
               return self.code_generation_node_name
            
            elif not self.has_code_been_written_locally:
                return self.write_generated_code_node_name
        
        return self.update_state_node_name
    
    def update_state(self, state: TestCoderState) -> TestCoderState:
        """
        This method updates the current state of the Architect agent with the provided state. 

        Args:
            state (ArchitectState): The new state to update the current state of the agent with.

        Returns:
            ArchitectState: The updated state of the agent.
        """
        logger.info(f"----{self.agent_name}: Proceeding with state update----")
        
        self.state = {**state}

        return {**self.state}
    

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
        
        if self.state['code'] is None:
            self.state["code"] = current_cg['code']
        else:
            state_ifc = current_cg['code'].copy()

            for key in state_ifc:
                if key in self.state['code']:
                    del current_cg['code'][key]   
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

        if self.state['current_task'].task_status == Status.NEW:
            self.mode = "test_code_generation"
            # self.is_segregated=False
            self.is_code_generated = False
            self.is_skeleton_generated=False
            self.has_command_execution_finished = False
            self.has_skeleton_been_written_locally=False
            self.has_code_been_written_locally = False
            self.is_license_file_downloaded = False
            self.is_license_text_added_to_files = False

            self.current_code_generation = {}

        return {**self.state}
    

    
    def test_code_generation_node(self, state: TestCoderState) -> TestCoderState:
        """
        """
        logger.info(f"----{self.agent_name}: Initiating Unit test code Generation----")

        self.update_state(state)
        self.last_visited_node = self.code_generation_node_name

        task = self.state["current_task"]

        logger.info(f"----{self.agent_name}: Started working on the task: {task.description}.----")
  
        self.add_message((
            ChatRoles.USER.value,
            f"Started working on the task: {task.description}."
        ))
        logger.info("llm callinig ")
        try:
            llm_response = self.test_code_generation_chain.invoke({
                "project_name": self.state['project_name'],
                "project_path": self.state['project_path'],
                "requirements_document": self.state['requirements_document'],
                "folder_structure": self.state['project_folder_strucutre'],
                "task": task.description,
                "error_message": self.error_message,
                "functions_skeleton":self.state["functions_skeleton"]
            })
            # logger.info("Called llm response is :" ,llm_response)
            # with open('/home/pranay/Desktop/Generatedfiles/latest/new_file_llmtest.txt', 'w') as file:
            #     file.write(str(llm_response))
            self.hasError = False
            self.error_message = ""

            required_keys = ["files_to_create", "code", "infile_license_comments", "commands_to_execute"]
            missing_keys = [key for key in required_keys if key not in llm_response]

            if missing_keys:
                raise KeyError(f"Missing keys: {missing_keys} in the response. Try Again!")

            self.update_state_test_code_generation(llm_response)
            self.current_code_generation["code"] = llm_response['code']
            self.current_code_generation["files_created"] = llm_response['files_to_create']
            self.current_code_generation['infile_license_comments'] = llm_response['infile_license_comments']
            self.current_code_generation['commands_to_execute'] = llm_response['commands_to_execute']

            self.add_message((
                ChatRoles.USER.value,
                f"{self.agent_name}: Test Code Generation completed!"
            ))

            self.is_code_generated = True
            

        except Exception as e:
            logger.error(f"----{self.agent_name}: Error Occured at code generation: {str(e)}.----")

            self.hasError = True
            self.error_message = f"An error occurred while processing the request: {str(e)}"

            self.add_message((
                ChatRoles.USER.value,
                f"{self.agent_name}: {self.error_message}"
            ))
        
        return {**self.state}


    def skeleton_generation_node(self, state: TestCoderState) -> TestCoderState:
        """
        """
        logger.info(f"----{self.agent_name}: Initiating skeleton Generation----")

        self.update_state(state)
        self.last_visited_node = self.skeleton_generation_node_name

        task = self.state["current_task"]

        logger.info(f"----{self.agent_name}: Started working on the task: {task.description}.----")
  
        self.add_message((
            ChatRoles.USER.value,
            f"Started working on the task: {task.description}."
        ))

        try:
            llm_response = self.skeleton_generation_chain.invoke({
                "project_name": self.state['project_name'],
                "project_path": self.state['project_path'],
                "requirements_document": self.state['requirements_document'],
                "folder_structure": self.state['project_folder_strucutre'],
                "task": task.description,
                "error_message": self.error_message,
            })

            self.hasError = False
            self.error_message = ""


            required_keys = ["skeletons_to_create"]
            missing_keys = [key for key in required_keys if key not in llm_response]

            if missing_keys:
                raise KeyError(f"Missing keys: {missing_keys} in the response. Try Again!")

            # logger.info(llm_response)
            self.update_state_skeleton_generation(llm_response)
            self.current_code_generation["functions_skeleton"] = llm_response['skeletons_to_create']
            logger.info("after state",llm_response)
            self.add_message((
                ChatRoles.USER.value,
                f"{self.agent_name}: skeleton generation completed!"
            ))

            self.is_skeleton_generated = True
        except Exception as e:
            logger.error(f"----{self.agent_name}: Error Occured at skeleton generation: {str(e)}.----")

            self.hasError = True
            self.error_message = f"An error occurred while processing the request: {str(e)}"

            self.add_message((
                ChatRoles.USER.value,
                f"{self.agent_name}: {self.error_message}"
            ))
        
        return {**self.state}
    

    # def task_segregation_node(self, state: TestCoderState) -> TestCoderState:
    #     """
    #     """
    #     logger.info(f"----{self.agent_name}: Initiating segregation ----")

    #     self.update_state(state)
    #     self.last_visited_node = self.skeleton_generation_node_name

    #     task = self.state["current_task"]

    #     logger.info(f"----{self.agent_name}: Started working on the task: {task.description}.----")
  
    #     self.add_message((
    #         ChatRoles.USER.value,
    #         f"Started working on the task: {task.description}."
    #     ))

    #     try:
    #         llm_response = self.segregaion_chain.invoke({
    #             "work_package": self.state['work_package']
    #         })

    #         self.hasError = False
    #         self.error_message = ""


    #         required_keys = ["taskType"]
    #         missing_keys = [key for key in required_keys if key not in llm_response]

    #         if missing_keys:
    #             raise KeyError(f"Missing keys: {missing_keys} in the response. Try Again!")

    #         # TODO: Need to update these to the state such that it holds the past tasks following field details along current task with no duplicates.
    #         logger.info(llm_response)
    #         time.sleep(20)
    #         # self.update_state_skeleton_generation(llm_response)

    #         # TODO: maintian class variable (local to class) to hold the current task's CodeGenerationPlan object so that we are not gonna pass any extra
    #         # details to the code generation prompt - look self.current_code_generation
        
    #         self.current_code_generation["taskType"] = llm_response['taskType']
    #         logger.info("after state",llm_response)
    #         self.add_message((
    #             ChatRoles.USER.value,
    #             f"{self.agent_name}: segregation completed!"
    #         ))

    #         self.is_skeleton_generated = True
    #     except Exception as e:
    #         logger.error(f"----{self.agent_name}: Error Occured at segregation: {str(e)}.----")

    #         self.hasError = True
    #         self.error_message = f"An error occurred while processing the request: {str(e)}"

    #         self.add_message((
    #             ChatRoles.USER.value,
    #             f"{self.agent_name}: {self.error_message}"
    #         ))
        
    #     return {**self.state}
    
    


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
                    ChatRoles.USER.value,
                    f"Started executing the command: {command}, in the path: {path}."
                ))
                execution_result=Shell.execute_command.invoke({
                    "command": command,
                    "repo_path": path
                })
                #if the command is successfully executed, run the next command 
                if execution_result[0]==False:
                    self.add_message((
                    ChatRoles.USER.value,
                    f"Successfully executed the command: {command}, in the path: {path}. The output of the command execution is {execution_result[1]}"
                ))
                    #if there is any error in the command execution log the error in the error_message and return the state to router by marking the has error as true and 
                    #last visited node as code generation node to generate the code and commands again, with out running the next set of commands.
                elif execution_result[0]==True:
                    
                    self.hasError=True
                    self.last_visited_node = self.code_generation_node_name
                    self.error_message= f"Error Occured while executing the command: {command}, in the path: {path}. The output of the command execution is {execution_result[1]}. This is the dictionary of commands and the paths where the respective command are supposed to be executed you have generated in previous run: {self.current_code_generation['commands_to_execute']}"
                    self.add_message((
                    ChatRoles.USER.value,
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
                ChatRoles.USER.value,
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
                    ChatRoles.USER.value,
                    f"Started writing the skeleton to the file in the path: {path}."
                ))
                execution_result=CodeFileWriter.write_generated_code_to_file.invoke({
                    "generated_code": str(function_skeleton),
                    "file_path": path
                })

                #if the code successfully stored in the specifies path, write the next code in the file
                if execution_result[0]==False:
                    self.add_message((
                    ChatRoles.USER.value,
                    f"Successfully executed the command: , in the path: {path}. The output of the command execution is {execution_result[1]}"
                ))
                    
                   
                elif execution_result[0]==True:
                    
                    self.hasError=True
                    self.last_visited_node = self.code_generation_node_name
                    self.error_message= f"Error Occured while writing the skeleton in the path: {path}. The output of writing the skeleton to the file is {execution_result[1]}."
                    self.add_message((
                    ChatRoles.USER.value,
                    f"{self.agent_name}: {self.error_message}"
                ))
                # logger.error(self.error_message)

            self.has_skeleton_been_written_locally = True
        except Exception as e:
            logger.error(f"----{self.agent_name}: Error Occured while writing the skelton to the respective files : {str(e)}.----")

            self.hasError = True
            self.error_message = f"An error occurred while processing the request: {str(e)}"

            self.add_message((
                ChatRoles.USER.value,
                f"{self.agent_name}: {self.error_message}"
            ))

        return {**self.state}
    
    def write_code_node(self, state: TestCoderState) -> TestCoderState:
        """
        """

        logger.info(f"----{self.agent_name}: Writing the generated unit test code to the respective files in the specified paths ----")

        self.update_state(state)
        self.last_visited_node = self.write_generated_code_node_name

        try:
            for path, code in self.current_code_generation['code'].items():
                
                logger.info(f"----{self.agent_name}: Started writing the code to the file at the path: {path}.----")
    
                self.add_message((
                    ChatRoles.USER.value,
                    f"Started writing the code to the file in the path: {path}."
                ))
                execution_result=CodeFileWriter.write_generated_code_to_file.invoke({
                    "generated_code": code,
                    "file_path": path
                })

                #if the code successfully stored in the specifies path, write the next code in the file
                if execution_result[0]==False:
                    self.add_message((
                    ChatRoles.USER.value,
                    f"Successfully executed the command: , in the path: {path}. The output of the command execution is {execution_result[1]}"
                ))
                    
                    #if there is any error in writing the code to the files log the error in the error_message and return the state to router by marking the has error as true and 
                    #last visited node as code generation node to generate the code and, with out running the next set of writing the files.
                elif execution_result[0]==True:
                    
                    self.hasError=True
                    self.last_visited_node = self.code_generation_node_name
                    self.error_message= f"Error Occured while writing the code in the path: {path}. The output of writing the code to the file is {execution_result[1]}."
                    self.add_message((
                    ChatRoles.USER.value,
                    f"{self.agent_name}: {self.error_message}"
                ))
                # logger.error(self.error_message)

            self.has_code_been_written_locally = True
        except Exception as e:
            logger.error(f"----{self.agent_name}: Error Occured while writing the code to the respective files : {str(e)}.----")

            self.hasError = True
            self.error_message = f"An error occurred while processing the request: {str(e)}"

            self.add_message((
                ChatRoles.USER.value,
                f"{self.agent_name}: {self.error_message}"
            ))

        return {**self.state}
    