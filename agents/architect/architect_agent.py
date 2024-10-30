"""Architect Agent
This module contains the ArchitectAgent class which is responsible for
managing the state of the Architect agent, processing user inputs, and
generating appropriate responses.
"""
import os
from typing import Literal

from agents.agent.agent import Agent
from agents.architect.architect_state import ArchitectState
from llms.llm import LLM
from models.architect_models import (ProjectDetails, QueryResult, TaskOutput,
                                     TasksList)
from models.constants import ChatRoles, PStatus, Status
from models.models import RequirementsDocument, Task, TaskQueue
from prompts.architect_prompts import ArchitectPrompts
from tools.code import CodeFileWriter
from utils.logs.logging_utils import logger


class ArchitectAgent(Agent[ArchitectState, ArchitectPrompts]):
    """
    ArchitectAgent Class

    This class represents the Architect agent. It maintains the state of the
    agent, processes user inputs, and generates appropriate responses. It uses
    a chain of tools to parse the user input and generate a structured output.
    """

    # names of the graph node
    entry_node_name: str  # The entry point of the graph
    requirements_node_name: str  # Node for handling requirements generation
    additional_info_node_name: str  # Node for handling additional information request
    write_requirements_node_name: str  # Node for writing requirements to local file system
    tasks_separation_node_name: str  # Node for converting the tasks from string to list
    project_details_node_name: str  # Node for gathering project details
    update_state_node_name: str  # Node for updating the state

    # local state of this class which is not exposed
    # to the graph state
    mode: Literal["information_gathering", "document_generation"]  # information_gathering: when additional information is needed, document_generation: when a requirements document needs to be generated
    generation_step: int  # Represents the step at which the current document generation is

    has_error_occured: bool  # Indicates if an error occurred when completing a task
    are_tasks_separated: bool  # Indicates if tasks have been converted from a string to a list
    is_additional_info_provided: bool  # Indicates if additional information is provided when requested
    is_requirements_document_generated: bool  # Indicates if the requirements document has been generated
    is_requirements_document_saved: bool  # Indicates if the requirements document has been saved locally
    is_additional_info_requested: bool  # Indicates if this agent has requested for additional information
    are_project_details_provided: bool  # Indicates if project details have been provided

    last_visited_node: str  # The last node that was visited in the graph
    error_message: str  # The error message, if an error occurred

    def __init__(self, agent_id: str, agent_name: str, llm: LLM) -> None:
        """
        This method initializes the ArchitectAgent with a given Language Learning 
        Model (llm) and sets up the architect chain. The architect chain is a sequence
        of operations that the ArchitectAgent will perform to generate a solution 
        architecture.

        Args:
            llm (ChatOpenAI): The Language Learning Model to be used by the 
            ArchitectAgent.
        """
       
        super().__init__(
            agent_id,
            agent_name,
            ArchitectState(),
            ArchitectPrompts(),
            llm
        )

        self.entry_node_name = "entry"
        self.requirements_node_name = "requirements"
        self.additional_info_node_name = "additional_info"
        self.write_requirements_node_name = "write_requirements"
        self.tasks_separation_node_name = "tasks_seperation"
        self.project_details_node_name = "project_details"
        self.update_state_node_name = "state_update"

        self.mode = ""
        self.generation_step = 0

        self.has_error_occured = False
        self.are_tasks_seperated = False
        self.is_additional_info_provided = False
        self.is_requirements_document_saved = False
        self.is_additional_info_requested = False
        self.is_requirements_document_generated = False
        self.are_project_details_provided = False

        self.last_visited_node = self.entry_node_name  # entry point node
        self.error_message = ""

    def add_message(self, message: tuple[ChatRoles, str]) -> None:
        """
        Adds a single message to the messages field in the state.

        Args:
            message (tuple[str, str]): The message to be added.
        """

        self.state['messages'] += [message]

    def create_tasks_list(self, tasks_description: list) -> TaskQueue:
        """
        This method creates a list of Task objects from a given list of task 
        descriptions.
       
        Args:
            tasks_description (list): A list of strings where each string is a 
            description of a task.

        Returns:
            list[Task]: A list of Task objects. Each Task object has a 'description'
            attribute set from the input list and a 'status' attribute set as NEW.
        """

        logger.info(f"{self.agent_name}: Initiating the process of Task List Creation")

        tasks: TaskQueue = TaskQueue()

        for description in tasks_description:
            tasks.add_item(Task(
                description=description,
                task_status=Status.NEW
            ))

        return tasks

    def request_for_additional_info(self, response: TaskOutput) -> None:
        """
        This method is used when additional information is needed to complete a task.
        It updates the status of the current task to AWAITING and sets the question for 
        additional info.

        Args:
            response (TaskOutput): The output of the task that requires additional
            information.
        """

        logger.info(f"{self.agent_name}: Initiating request for additional information")

        self.is_additional_info_requested = True
        self.state['current_task'].question = response.question_for_additional_info
        self.state['current_task'].task_status = Status.AWAITING
   
    def update_requirements_overview(self, key: str, phase: str, response: TaskOutput):
        """
        This method is used to update the requirements overview with the content 
        generated by a task.

        Args:
            key (str): The key in the requirements overview to be updated.
            phase (str): The phase of the task.
            response (TaskOutput): The output of the task.
        """
        logger.info(f"{self.agent_name}: Modifying key: {key} in requirements overview")

        if not response.is_add_info_needed:
            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {phase} is now ready and prepared."
            ))
            self.state['requirements_document'][key] = response.content

            # update to next phase
            self.generation_step += 1
        else:
            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: Additional information requested by {phase}."
            ))
            self.request_for_additional_info(response)

    def handle_requirements_overview(self, response: TaskOutput) -> None:
        """
        This method handles the generation of the requirements overview based on the
        current generation step. It determines which section of the requirements 
        overview to update based on the generation step and calls the 
        'update_requirements_overview' method with the appropriate parameters.

        Args:
            response (TaskOutput): The output of the task. This contains the generated
            content for the current section of the requirements overview.
        """

        logger.info(f"{self.agent_name}: Progressing with requirements overview. Current Step: {self.generation_step}")

        if self.generation_step == 0:  # Project Overview
            self.update_requirements_overview("project_overview", "Project Overview", 
                                              response)
        elif self.generation_step == 1:  # Architecture
            self.update_requirements_overview("project_architecture", 
                                              "Architecture", response)
        elif self.generation_step == 2:  # Folder Structure
            self.update_requirements_overview("directory_structure", 
                                              "Folder Structure", response)
        elif self.generation_step == 3:  # Microservice Design
            self.update_requirements_overview("microservices_architecture", 
                                              "Microservice Design", response)
        elif self.generation_step == 4:  # Tasks Breakdown
            self.update_requirements_overview("tasks_overview", "Tasks Breakdown", 
                                              response)
        elif self.generation_step == 5:  # Standards
            self.update_requirements_overview("coding_standards", "Standards", 
                                              response)
        elif self.generation_step == 6:  # Implementation Details
            self.update_requirements_overview("implementation_process", 
                                              "Implementation Details", response)
        elif self.generation_step == 7:  # License Details
            self.update_requirements_overview("project_license_information", 
                                              "License Details", response)

    def router(self, state: ArchitectState) -> str:
        """
        This method acts as a router, determining the next step in the process based
        on the current state of the Architect agent. It checks the current state and 
        returns the name of the next agent to be invoked.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            str: The name of the next agent to be invoked.
        """

        logger.info(f"{self.agent_name}: Router in action: Determining the next node")

        if self.has_error_occured:
            return self.last_visited_node
        
        if self.is_additional_info_requested:
            return self.update_state_node_name
        
        if self.mode == "document_generation":
            if not self.is_requirements_document_generated:
                return self.requirements_node_name
            
            if not self.is_requirements_document_saved:
                return self.write_requirements_node_name
            
            if not self.are_tasks_seperated:
                return self.tasks_separation_node_name
            
            if not self.are_project_details_provided:
                return self.project_details_node_name
        elif self.mode == "information_gathering":
            if not self.is_additional_info_provided:
                return self.additional_info_node_name
       
        return self.update_state_node_name
   
    def entry_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method is the entry point of the Architect agent. It updates the current
        state with the provided state and sets the mode based on the project status and
        the status of the current task.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """

        logger.info(f"{self.agent_name}: Initiating Graph Entry Point")

        state['tasks'] = TaskQueue()
        self.state = state
        self.last_visited_node = self.entry_node_name
        self.is_additional_info_requested = False

        # TODO: Improvise conditional check with more details its too hard 
        # understand the scenarios add detailed comments as well
        if self.state['project_status'] == PStatus.INITIAL:
            if self.state['current_task'].task_status == Status.INPROGRESS:
                self.is_requirements_document_generated = False
                self.is_requirements_document_saved = False
                self.are_tasks_seperated = False
                self.are_project_details_provided = False
            self.mode = "document_generation"
        elif self.state["current_task"].task_status == Status.AWAITING:
            self.mode = "information_gathering"

        return self.state

    def requirements_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method is responsible for generating the requirements overview.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """
        logger.info(f"{self.agent_name}: Commencing generation of Requirements Document")

        if (not self.has_error_occured) and (not self.is_additional_info_requested):
            state['requirements_document'] = RequirementsDocument()
            self.generation_step = 0
           
        self.state = state
        self.last_visited_node = self.requirements_node_name
        self.is_additional_info_requested = False

        self.add_message((
            ChatRoles.USER,
            f"{self.agent_name}: Preparing the requirements overview."
        ))

        additional_info = f"{self.state['current_task'].additional_info}"
        logger.debug(f"{self.agent_name}: Additional Information - {additional_info}")
        logger.info(f"{self.agent_name}: Additional Information - {additional_info}")
        try:
            if self.generation_step == 0:  # 0. Project Overview
                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: Progressing with Step 0 - project_overview."
                ))

                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.project_overview_prompt, 
                    {
                        "user_request": f"{self.state['original_user_input']}",
                        "task_description": f"{self.state['current_task'].description}",
                        "additional_information": additional_info
                    }, 
                    TaskOutput
                )

                self.has_error_occured = False
                self.error_message = ""
                self.handle_requirements_overview(llm_output.response)

            if self.generation_step == 1:  # 1. Architecture
                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: Progressing with Step 1 - Architecture."
                ))

                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.architecture_prompt, 
                    {
                        "project_overview": f"{self.state['requirements_document'].project_overview}",
                        "additional_information": additional_info
                    }, 
                    TaskOutput
                )

                self.has_error_occured = False
                self.error_message = ""
                self.handle_requirements_overview(llm_output.response)

            if self.generation_step == 2:  # 2. Folder Structure
                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: Progressing with Step 2 - Folder Structure."
                ))

                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.folder_structure_prompt,
                    {
                        "project_overview": f"{self.state['requirements_document'].project_overview}",
                        "architecture": f"{self.state['requirements_document'].project_architecture}",
                        "additional_information": additional_info
                    }, 
                    TaskOutput
                )

                self.has_error_occured = False
                self.error_message = ""
                self.handle_requirements_overview(llm_output.response)

            if self.generation_step == 3:  # 3. Micro service Design
                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: Progressing with Step 3 - Microservice Design."
                ))

                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.microservice_design_prompt, 
                    {
                        "project_overview": f"{self.state['requirements_document'].project_overview}",
                        "architecture": f"{self.state['requirements_document'].project_architecture}",
                        "additional_information": additional_info
                    }, 
                    TaskOutput
                )

                self.has_error_occured = False
                self.error_message = ""
                self.handle_requirements_overview(llm_output.response)

            if self.generation_step == 4:  # 4. Tasks Breakdown
                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: Progressing with Step 4 - Tasks Breakdown."
                ))

                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.tasks_breakdown_prompt,
                    {
                        "project_overview": f"{self.state['requirements_document'].project_overview}",
                        "architecture": f"{self.state['requirements_document'].project_architecture}",
                        "microservice_design": f"{self.state['requirements_document'].microservices_architecture}",
                        "additional_information": additional_info
                    },
                    TaskOutput
                )

                self.has_error_occured = False
                self.error_message = ""
                self.handle_requirements_overview(llm_output.response)

            if self.generation_step == 5:  # 5. Standards
                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: Progressing with Step 5 - Standards."
                ))

                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.standards_prompt,
                    {
                        "user_request": f"{self.state['original_user_input']}\n",
                        "task_description": f"{self.state['requirements_document'].tasks_overview}",
                        "additional_information": additional_info
                    },
                    TaskOutput
                )

                self.has_error_occured = False
                self.error_message = ""
                self.handle_requirements_overview(llm_output.response)

            if self.generation_step == 6:  # 6. Implementation Details
                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: Processing Step 6 - Implementation Details."
                ))

                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.implementation_details_prompt,
                    {
                        "architecture": f"{self.state['requirements_document'].project_architecture}\n",
                        "microservice_design": f"{self.state['requirements_document'].microservices_architecture}",
                        "folder_structure": f"{self.state['requirements_document'].directory_structure}",
                        "additional_information": additional_info
                    },
                    TaskOutput
                )

                self.has_error_occured = False
                self.error_message = ""
                self.handle_requirements_overview(llm_output.response)

            if self.generation_step == 7:  # 7. License Details
                self.add_message((
                    ChatRoles.USER,
                    f"{self.agent_name}: Progressing with Step 7 - License Details."
                ))

                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.license_details_prompt,
                    {
                        "user_request": f"{self.state['original_user_input']}",
                        "license_text": f"{self.state['license_text']}",
                        "additional_information": additional_info
                    },
                    TaskOutput
                )

                self.has_error_occured = False
                self.error_message = ""
                self.handle_requirements_overview(llm_output.response)

            if self.generation_step == 8:
                self.is_requirements_document_generated = True
        except Exception as e:
            self.has_error_occured = True
            self.error_message = f"An error occurred while processing the request: {e}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))
            logger.debug(f"{e}")
            logger.error(
                f"Exception: {type(e)} --> {self.agent_name}: {self.error_message}"
            )

        return self.state

    def write_requirements_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method is used to write the requirements overview to a local file. It 
        updates the state of the architect and sets the `is_requirements_document_saved`
        flag to True if the requirements are successfully written.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """

        logger.info(f"{self.agent_name}: Writing requirements documents to local filesystem")

        self.state=state

        document = self.state['requirements_document'].to_markdown()
        if len(document) < 0:
            self.has_error_occured = True
            self.error_message = (
                "ERROR: Found requirements document to be empty. "
                "Could not write it to file system."
            )
            self.last_visited_node = self.requirements_node_name
           
            self.add_message((
                ChatRoles.USER,
                self.error_message,
            ))
        else:
            generated_code = document
            file_path = os.path.join(self.state['project_path'], "docs/requirements.md")

            self.has_error_occured, msg = CodeFileWriter.write_generated_code_to_file.invoke(
                {"generated_code": generated_code, "file_path": file_path}
            )

            self.has_error_occured = False
            self.error_message = ""
            self.last_visited_node = self.write_requirements_node_name
            self.is_requirements_document_saved = True

            self.add_message((
                ChatRoles.USER,
                msg
            ))

        return self.state

    def tasks_separation_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method separates tasks from the requirements document and creates a list
        of tasks. It updates the state of the architect with the separated tasks.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """

        logger.info(f"{self.agent_name}: Initiating the process of Tasks Separation")

        self.state = state
        self.last_visited_node = self.tasks_separation_node_name

        try:
            llm_output = self.llm.invoke_with_pydantic_model(
                self.prompts.tasks_separation_prompt, 
                {
                    "tasks": self.state['requirements_document'].tasks_overview,
                    "error_message": self.error_message
                }, 
                TasksList
            )

            self.has_error_occured = False
            self.error_message = ""

            self.state['tasks'].extend(
                self.create_tasks_list(llm_output.response.tasks)
            )

            self.are_tasks_seperated = True
            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: Task list has been successfully created. You can now proceed with your tasks."
            ))

        except ValueError as ve:
            self.has_error_occured = True
            self.error_message = f"ValueError occurred: {ve}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))
            logger.error(
                f"Exception: {type(ve)} --> {self.agent_name}: {self.error_message}"
            )
        except TypeError as te:
            self.has_error_occured = True
            self.error_message = f"TypeError occurred: {te}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))
            logger.error(
                f"Exception: {type(te)} --> {self.agent_name}: {self.error_message}"
            )
        except Exception as e:
            self.has_error_occured = True
            self.error_message = f"An unexpected error occurred: {e}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))     
            logger.error(
                f"Exception: {type(e)} --> {self.agent_name}: {self.error_message}"
            )

        return self.state

    def project_details_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method is used to gather project details. It updates the current state with
        the provided state and invokes the project_details_prompt to get the project
        details.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """

        logger.info(f"{self.agent_name}: Initiating the process of gathering project details")

        self.state = state
        self.last_visited_node = self.project_details_node_name

        self.add_message((
            ChatRoles.USER,
            f"{self.agent_name}: Initiating the process of gathering project details."
        ))

        try:
            llm_output = self.llm.invoke_with_pydantic_model(
                self.prompts.project_details_prompt,
                {
                    "user_request": f"{self.state['original_user_input']}\n",
                    "error_message": f"{self.error_message}\n",
                },
                ProjectDetails
            )

            self.has_error_occured = False
            self.error_message = ""

            self.state['project_name'] = llm_output.response.project_name

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: Project details have been successfully gathered!"
            ))

            self.are_project_details_provided = True
            self.state['current_task'].task_status = Status.DONE
        except Exception as e:
            self.has_error_occured = True
            self.error_message = f"An error occurred while processing the request: {e}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))

            logger.error(
                f"Exception: {type(e)} --> {self.agent_name}: {self.error_message}"
            )

        return self.state
   
    def additional_information_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method is used to gather additional information if needed. It updates the
        current state with the provided state and invokes the additional_information_prompt
        to get the additional information.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """
       
        logger.info(f"{self.agent_name}: Working on gathering additional information")

        self.state = state
        self.last_visited_node = self.additional_info_node_name

        self.add_message((
            ChatRoles.USER,
            f"{self.agent_name}: Gathering additional information."
        ))
       
        try:
            llm_output = self.llm.invoke_with_pydantic_model(
                self.prompts.additional_info_prompt,
                {
                    "requirements_document": self.state['requirements_document'].to_markdown(),
                    "question": self.state['current_task'].question,
                    "error_message": self.error_message
                },
                QueryResult
            )

            self.has_error_occured = False
            self.error_message = ""

            self.state["query_answered"] = llm_output.response.is_answer_found
          
            response_text = (
                llm_output.response.response_text 
                if self.state["query_answered"] 
                else "I don't have any additional information about the question."
            )
            self.state["current_task"].additional_info = (
                f"{self.state['current_task'].additional_info},"
                f" \nArchitect_Response:\n{response_text}"
            )

            message_text = (
                "Additional information successfully provided."
                if self.state["query_answered"]
                else "Unable to provide the requested additional information."
            )

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {message_text}"
            ))

            self.is_additional_info_provided = True
        except Exception as e:
            self.has_error_occured = True
            self.error_message = f"An error occurred while processing the request: {e}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.error_message}"
            ))

            logger.error(
                f"Exception: {type(e)} --> {self.agent_name}: {self.error_message}"
            )

        return self.state
