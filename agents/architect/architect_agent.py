"""Architect Agent
This module contains the ArchitectAgent class which is responsible for
managing the state of the Architect agent, processing user inputs, and
generating appropriate responses.
"""
import os

from agents.architect.architect_state import ArchitectState
from agents.base.base_agent import BaseAgent
from llms.llm import LLM
from models.architect_models import (ProjectDetails, QueryResult, TaskOutput,
                                     TasksList)
from models.constants import ChatRoles, PStatus, Status
from models.models import RequirementsDocument, Task, TaskQueue
from prompts.architect_prompts import ArchitectPrompts
from tools.code import CodeFileWriter
from utils.logs.logging_utils import logger


class ArchitectAgent(BaseAgent[ArchitectState, ArchitectPrompts]):
    """
    ArchitectAgent Class

    This class represents the Architect agent. It maintains the state of the
    agent, processes user inputs, and generates appropriate responses. It uses
    a chain of tools to parse the user input and generate a structured output.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        llm: LLM
    ) -> None:
        """
        Initializes the ArchitectAgent with a given Language Learning Model (LLM) and
        sets up the architect chain for solution architecture generation.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Name of the agent.
            llm (LLM): The Language Learning Model to be used by the ArchitectAgent.
        """
       
        super().__init__(
            agent_id,
            agent_name,
            ArchitectState(),
            ArchitectPrompts(),
            llm
        )

        # Define the graph node names
        self.entry_node_name = "entry"  # The entry point of the graph
        self.requirements_node_name = "requirements"  # Node for handling requirements generation
        self.additional_info_node_name = "additional_info"  # Node for handling additional information request
        self.write_requirements_node_name = "write_requirements"  # Node for writing requirements to local file system
        self.tasks_separation_node_name = "tasks_seperation"  # Node for converting the tasks from string to list
        self.project_details_node_name = "project_details"  # Node for gathering project details
        self.update_state_node_name = "state_update"  # Node for updating the state

    def add_message(self, message: tuple[ChatRoles, str]) -> None:
        """
        Adds a single message to the messages field in the state.

        Args:
            message (tuple[str, str]): The message to be added.
        """

        logger.debug(f"{self.agent_name}: Adding message: {message}")
        self.state['messages'] += [message]

    def create_tasks_list(self, tasks_description: list) -> TaskQueue:
        """
        Creates a list of Task objects from a given list of task descriptions.

        Args:
            tasks_description (list): A list of strings where each string is a
            description of a task.

        Returns:
            TaskQueue: A queue containing Task objects.
        """

        logger.info(f"{self.agent_name}: Creating a task list from descriptions.")
        tasks: TaskQueue = TaskQueue()

        for description in tasks_description:
            logger.debug(f"Creating task: {description}")
            tasks.add_item(Task(
                description=description,
                task_status=Status.NEW
            ))

        logger.info(f"{self.agent_name}: Task list created with {len(tasks)} tasks.")
        return tasks

    def request_for_additional_info(self, response: TaskOutput) -> None:
        """
        Requests additional information to complete a task.

        Args:
            response (TaskOutput): The output of the task that requires additional
            information.
        """

        logger.info(f"{self.agent_name}: Requesting additional information for task.")
        self.state['is_additional_info_requested'] = True
        self.state['current_task'].question = response.question_for_additional_info
        self.state['current_task'].task_status = Status.AWAITING
        logger.debug(f"Updated task question: {response.question_for_additional_info}")

    def update_requirements_overview(
        self,
        key: str,
        phase: str,
        response: TaskOutput
    ) -> None:
        """
        Updates the requirements overview with generated content.

        Args:
            key (str): The key in the requirements overview to be updated.
            phase (str): The phase of the task.
            response (TaskOutput): The output of the task.
        """
        logger.info(f"{self.agent_name}: Updating requirements overview for {phase}.")
        if not response.is_add_info_needed:
            logger.debug(f"Content generated successfully for {phase}.")
            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {phase} is now ready and prepared."
            ))
            self.state['requirements_document'][key] = response.content
            self.state['generation_step'] += 1
        else:
            logger.warning(f"{self.agent_name}: Additional information required for {phase}.")
            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: Additional information requested by {phase}."
            ))
            self.request_for_additional_info(response)

    def handle_requirements_overview(self, response: TaskOutput) -> None:
        """
        Handles the generation of the requirements overview based on the current step.

        Args:
            response (TaskOutput): The output of the task.
        """

        logger.info(
            f"{self.agent_name}: Handling requirements overview. "
            f"Step: {self.state['generation_step']}"
        )
        steps = [
            ("project_overview", "Project Overview"),
            ("project_architecture", "Architecture"),
            ("directory_structure", "Folder Structure"),
            ("microservices_architecture", "Microservice Design"),
            ("tasks_overview", "Tasks Breakdown"),
            ("coding_standards", "Standards"),
            ("implementation_process", "Implementation Details"),
            ("project_license_information", "License Details")
        ]
        if self.state['generation_step'] < len(steps):
            key, phase = steps[self.state['generation_step']]
            self.update_requirements_overview(key, phase, response)
        else:
            logger.error(
                f"{self.agent_name}: Invalid generation step "
                f"{self.state['generation_step']}."
            )

    def router(self, state: ArchitectState) -> str:
        """
        Determines the next step in the process based on the current state.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            str: The name of the next node to be invoked.
        """

        logger.info(
            f"{self.agent_name}: Routing to the next node based on current "
            f"state."
        )
        if state['has_error_occured']:
            logger.warning(
                f"{self.agent_name}: Routing back to last visited node due to an "
                f"error: {state['last_visited_node']}"
            )
            return state['last_visited_node']
        
        if state['is_additional_info_requested']:
            logger.debug(
                f"{self.agent_name}: Routing to state update node for additional info."
            )
            return self.update_state_node_name
        
        if state['mode'] == "document_generation":
            if not state['is_requirements_document_generated']:
                return self.requirements_node_name
            if not state['is_requirements_document_saved']:
                return self.write_requirements_node_name
            if not state['are_tasks_seperated']:
                return self.tasks_separation_node_name
            if not state['are_project_details_provided']:
                return self.project_details_node_name
        elif state['mode'] == "information_gathering":
            if not state['is_additional_info_provided']:
                return self.additional_info_node_name
        
        logger.debug(f"{self.agent_name}: Defaulting to state update node.")
        return self.update_state_node_name
   
    def entry_node(self, state: ArchitectState) -> ArchitectState:
        """
        Entry point for the Architect agent.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """
        logger.info(f"{self.agent_name}: Entry node invoked.")

        state['tasks'] = TaskQueue()
        self.state = state
        self.state['last_visited_node'] = self.entry_node_name
        self.state['is_additional_info_requested'] = False
        
        default_state_values = {
            'generation_step': 0,
            'has_error_occured': False,
            'are_tasks_seperated': False,
            'is_additional_info_provided': False,
            'is_requirements_document_generated': False,
            'is_additional_info_requested': False,
            'are_project_details_provided': False,
            'error_message': ""
        }
        for key, value in default_state_values.items():
            self.state[key] = BaseAgent.ensure_value(self.state.get(key), value)
            logger.debug(f"{self.agent_name}: {key} set to {self.state[key]}.")
        
        # TODO: Improvise conditional check with more details its too hard 
        # understand the scenarios. add detailed comments as well
        if self.state['project_status'] == PStatus.INITIAL:
            logger.info(f"{self.agent_name}: Project status is INITIAL.")
            if self.state['current_task'].task_status == Status.INPROGRESS:
                self.state['is_requirements_document_generated'] = False
                self.state['is_requirements_document_saved'] = False
                self.state['are_tasks_seperated'] = False
                self.state['are_project_details_provided'] = False
            self.state['mode'] = "document_generation"
        elif self.state["current_task"].task_status == Status.AWAITING:
            logger.info(
                f"{self.agent_name}: Task status is AWAITING. Switching to information"
                " gathering mode."
            )
            self.state['mode'] = "information_gathering"

        return self.state

    def requirements_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method is responsible for generating the requirements overview.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """
        logger.info(f"{self.agent_name}: Starting requirements document generation.")

        if (not self.state['has_error_occured']) and (not self.state['is_additional_info_requested']):
            state['requirements_document'] = RequirementsDocument()
            self.state['generation_step'] = 0
           
        self.state = state
        self.state['last_visited_node'] = self.requirements_node_name
        self.state['is_additional_info_requested'] = False

        self.add_message((
            ChatRoles.USER,
            f"{self.agent_name}: Preparing the requirements overview."
        ))

        additional_info = f"{self.state['current_task'].additional_info}"
        logger.debug(f"{self.agent_name}: Additional Information: {additional_info}")

        try:
            if self.state['generation_step'] == 0:  # 0. Project Overview
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

                self.state['has_error_occured'] = False
                self.state['error_message'] = ""
                self.handle_requirements_overview(llm_output.response)

            if self.state['generation_step'] == 1:  # 1. Architecture
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

                self.state['has_error_occured'] = False
                self.state['error_message'] = ""
                self.handle_requirements_overview(llm_output.response)

            if self.state['generation_step'] == 2:  # 2. Folder Structure
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

                self.state['has_error_occured'] = False
                self.state['error_message'] = ""
                self.handle_requirements_overview(llm_output.response)

            if self.state['generation_step'] == 3:  # 3. Micro service Design
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

                self.state['has_error_occured'] = False
                self.state['error_message'] = ""
                self.handle_requirements_overview(llm_output.response)

            if self.state['generation_step'] == 4:  # 4. Tasks Breakdown
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

                self.state['has_error_occured'] = False
                self.state['error_message'] = ""
                self.handle_requirements_overview(llm_output.response)

            if self.state['generation_step'] == 5:  # 5. Standards
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

                self.state['has_error_occured'] = False
                self.state['error_message'] = ""
                self.handle_requirements_overview(llm_output.response)

            if self.state['generation_step'] == 6:  # 6. Implementation Details
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

                self.state['has_error_occured'] = False
                self.state['error_message'] = ""
                self.handle_requirements_overview(llm_output.response)

            if self.state['generation_step'] == 7:  # 7. License Details
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

                self.state['has_error_occured'] = False
                self.state['error_message'] = ""
                self.handle_requirements_overview(llm_output.response)

            if self.state['generation_step'] == 8:
                logger.info(
                    f"{self.agent_name}: All steps completed. Requirements document "
                    "generated."
                )
                self.state['is_requirements_document_generated'] = True
        except Exception as e:
            self.state['has_error_occured'] = True
            self.state['error_message'] = f"An error occurred while processing the request: {e}"

            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: {self.state['error_message']}"
            ))
            logger.error(f"Exception in {self.agent_name}: {e}", exc_info=True)

        return self.state

    def write_requirements_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method writes the requirements overview to a local file.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """
        logger.info(f"{self.agent_name}: Writing requirements document to local filesystem.")

        self.state=state
        document = self.state['requirements_document'].to_markdown()

        if not document.strip():
            self.state['has_error_occured'] = True
            self.state['error_message'] = (
                "The requirements document is empty. Writing aborted."
            )
            logger.error(self.state['error_message'])
            self.state['last_visited_node'] = self.requirements_node_name
            self.add_message((ChatRoles.USER, self.state['error_message']))
        else:
            file_path = os.path.join(self.state['project_path'], "docs/requirements.md")
            logger.debug(f"{self.agent_name}: Writing to {file_path}.")

            try:
                success, msg = CodeFileWriter.write_generated_code_to_file.invoke({
                    "generated_code": document,
                    "file_path": file_path
                })

                self.state['has_error_occured'] = not success
                self.state['error_message'] = "" if success else "Failed to write requirements document."
                self.state['last_visited_node'] = self.write_requirements_node_name
                self.state['is_requirements_document_saved'] = success
                self.add_message((ChatRoles.USER, msg))
            except Exception as e:
                self.state['has_error_occured'] = True
                self.state['error_message'] = f"Error writing requirements document: {e}"
                logger.error(self.state['error_message'], exc_info=True)

        return self.state

    def tasks_separation_node(self, state: ArchitectState) -> ArchitectState:
        """
        Separates tasks from the requirements document and creates a task list.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """
        logger.info(f"{self.agent_name}: Separating tasks from the requirements document.")

        self.state = state
        self.state['last_visited_node'] = self.tasks_separation_node_name


        try:
            llm_output = self.llm.invoke_with_pydantic_model(
                self.prompts.tasks_separation_prompt, 
                {
                    "tasks": self.state['requirements_document'].tasks_overview,
                    "error_message": self.state['error_message']
                }, 
                TasksList
            )

            self.state['has_error_occured'] = False
            self.state['error_message'] = ""

            self.state['tasks'].extend(
                self.create_tasks_list(llm_output.response.tasks)
            )
            self.state['are_tasks_seperated'] = True
            self.add_message((
                ChatRoles.USER,
                f"{self.agent_name}: Tasks successfully separated."
            ))
        except Exception as e:
            self.state['has_error_occured'] = True
            self.state['error_message'] = f"Task separation failed: {e}"
            logger.error(self.state['error_message'], exc_info=True)
            self.add_message((ChatRoles.USER, self.state['error_message']))

        return self.state

    def project_details_node(self, state: ArchitectState) -> ArchitectState:
        """
        Gathers project details and updates the state.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """
        logger.info(f"{self.agent_name}: Gathering project details.")

        self.state = state
        self.state['last_visited_node'] = self.project_details_node_name

        try:
            llm_output = self.llm.invoke_with_pydantic_model(
                self.prompts.project_details_prompt,
                {
                    "user_request": f"{self.state['original_user_input']}\n",
                    "error_message": f"{self.state['error_message']}\n",
                },
                ProjectDetails
            )

            self.state['has_error_occured'] = False
            self.state['error_message'] = ""

            self.state['project_name'] = llm_output.response.project_name
            self.add_message((ChatRoles.USER, f"{self.agent_name}: Project details gathered successfully."))
            self.state['are_project_details_provided'] = True
            self.state['current_task'].task_status = Status.DONE
        except Exception as e:
            self.state['has_error_occured'] = True
            self.state['error_message'] = f"Error gathering project details: {e}"
            logger.error(self.state['error_message'], exc_info=True)
            self.add_message((ChatRoles.USER, self.state['error_message']))

        return self.state
   
    def additional_information_node(self, state: ArchitectState) -> ArchitectState:
        """
        Gathers additional information if required.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """
        logger.info(f"{self.agent_name}: Gathering additional information.")

        self.state = state
        self.state['last_visited_node'] = self.additional_info_node_name

        try:
            llm_output = self.llm.invoke_with_pydantic_model(
                self.prompts.additional_info_prompt,
                {
                    "requirements_document": self.state['requirements_document'].to_markdown(),
                    "question": self.state['current_task'].question,
                    "error_message": self.state['error_message']
                },
                QueryResult
            )

            self.state['has_error_occured'] = False
            self.state['error_message'] = ""

            self.state["query_answered"] = llm_output.response.is_answer_found
            response_text = (
                llm_output.response.response_text 
                if self.state["query_answered"] 
                else "No additional information available."
            )
            self.state['current_task'].additional_info += f"\nArchitect Response:\n{response_text}"
            self.add_message((ChatRoles.USER, f"{self.agent_name}: {response_text}"))

            self.state['is_additional_info_provided'] = True
        except Exception as e:
            self.state['has_error_occured'] = True
            self.state['error_message'] = f"Error gathering additional information: {e}"
            logger.error(self.state['error_message'], exc_info=True)
            self.add_message((ChatRoles.USER, self.state['error_message']))

        return self.state
