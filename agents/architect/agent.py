"""Architect Agent

This module contains the ArchitectAgent class which is responsible for 
managing the state of the Architect agent, processing user inputs, and 
generating appropriate responses.
"""

from langgraph.prebuilt import ToolExecutor

from langchain_core.runnables.base import RunnableSequence

from langchain_core.output_parsers import JsonOutputParser

from prompts.architect import ArchitectPrompts

from models.constants import PStatus
from models.constants import Status
from models.constants import ChatRoles

from models.models import Task

from models.architect import RequirementsOverview, TaskOutput, TasksList
from models.architect import QueryResult

from agents.architect.state import ArchitectState

from tools.code import CodeFileWriter

from typing_extensions import Literal

import os

class ArchitectAgent:
    """
    ArchitectAgent Class

    This class represents the Architect agent. It maintains the state of the
    agent, processes user inputs, and generates appropriate responses. It uses 
    a chain of tools to parse the user input and generate a structured output.
    """
    agent_name: str = "Solution Architect"

    # names of the graph node
    entry: str = "entry"
    requirements: str = "requirements"
    additional_info: str = "additional_info"
    write_requirements: str = "write_requirements"
    tasks_seperation: str = "tasks_seperation"
    state_update: str = "state_update"

    # local state of this class which is not exposed
    # to the graph state
    mode: Literal["gather_info", "generation"] # gather_info: when additional information need, generation: need to generate requirements document
    generation_phase: int # at step which current generation is

    has_error: bool
    are_tasks_seperated: bool
    is_additional_info_provided: bool
    are_requirements_generated: bool
    are_requirements_saved_to_local: bool
    requested_for_additional_info: bool

    last_visited_node: str
    error_message: str

    # tools used by this agent
    tools: ToolExecutor

    state: ArchitectState = ArchitectState()
    prompts: ArchitectPrompts = ArchitectPrompts()

    # chains
    project_overview_chain: RunnableSequence
    architecture_chain: RunnableSequence
    folder_structure_chain: RunnableSequence
    microservice_design_chain: RunnableSequence
    tasks_breakdown_chain: RunnableSequence
    standards_chain: RunnableSequence
    implementation_details_chain: RunnableSequence
    license_legal_chain: RunnableSequence

    additional_information_chain: RunnableSequence
    task_seperation_chain: RunnableSequence

    def __init__(self, llm) -> None:
        """
        Initializes the ArchitectAgent with a given Language Learning Model
        (llm) and sets up the architect chain.
        """

        self.has_error = False
        self.are_tasks_seperated = False
        self.is_additional_info_provided = False
        self.are_requirements_saved_to_local = False
        self.requested_for_additional_info = False
        self.are_requirements_generated = False

        self.mode = ""
        self.generation_phase = 0
        self.last_visited_node = self.entry # entry point node

        self.error_message = ""

        self.llm = llm
        self.tools = ToolExecutor([CodeFileWriter.write_generated_code_to_file])

        self.project_overview_chain = ( 
            self.prompts.project_overview_prompt
            | self.llm
            | JsonOutputParser()
        )

        self.architecture_chain = (
            self.prompts.architecture_prompt
            | self.llm
            | JsonOutputParser()
        )

        self.folder_structure_chain = (
            self.prompts.folder_structure_prompt
            | self.llm
            | JsonOutputParser()
        )

        self.microservice_design_chain = (
            self.prompts.microservice_design_prompt
            | self.llm
            | JsonOutputParser()
        )

        self.tasks_breakdown_chain = (
            self.prompts.tasks_breakdown_prompt
            | self.llm
            | JsonOutputParser()
        )

        self.standards_chain = (
            self.prompts.standards_prompt
            | self.llm
            | JsonOutputParser()
        )

        self.implementation_details_chain = (
            self.prompts.implementation_details_prompt
            | self.llm
            | JsonOutputParser()
        )

        self.license_legal_chain = (
            self.prompts.license_details_prompt
            | self.llm
            | JsonOutputParser()
        )

        # This chain is used when team member requests for additional information to complete 
        # the task
        self.additional_information_chain = (
            self.prompts.additional_info_prompt
            | self.llm
            | JsonOutputParser()
        )

        # This chain is used when we need to create a list of tasks from the markdown formatted
        # tasks
        self.task_seperation_chain = (
            self.prompts.tasks_seperation_prompt
            | self.llm
            | JsonOutputParser()
        )

    def create_requirements_document(self) -> str:
        """
        """
        
        print(f"----{self.agent_name}: Creating requirements document----")

        return f"""
# Project Requirements Document

{self.state['requirements_overview']['project_details']}

{self.state['requirements_overview']['architecture']}

{self.state['requirements_overview']['folder_structure']}

{self.state['requirements_overview']['microservice_design']}

{self.state['requirements_overview']['task_description']}

{self.state['requirements_overview']['standards']}

{self.state['requirements_overview']['implementation_details']}

{self.state['requirements_overview']['license_details']}
        """
    
    def create_tasks(self, tasks: list) -> list[Task]:
        """
        This method is used to create a list of Task objects from a string representation of a list.

        Args:
            tasks (list): A list where each element is a description of a task.

        Returns:
            list[Task]: A list of Task objects with the description set from the input and the status 
            set as NEW.
        """

        print(f"----{self.agent_name}: Creating List of Tasks----")
        # ts_list = ast.literal_eval(tasks)
        tasks_list: list[Task] = []

        for ti in tasks:
            tasks_list.append(Task(
                description=ti,
                task_status=Status.NEW
            ))   

        return tasks_list

    def add_message(self, message: tuple[str, str]) -> None:
        """
        Adds a single message to the messages field in the state.

        Args:
            message (tuple[str, str]): The message to be added.
        """

        self.state['messages'] += [message]

    def request_additional_info(self, response: TaskOutput) -> None:
        """
        """

        self.requested_for_additional_info = True
        self.state['current_task'].question = response['question_for_additional_info']
        self.state['current_task'].task_status = Status.AWAITING
    
    def update_requirements_overview(self, key: str, phase: str, response: TaskOutput) -> None:
        """
        """

        if not response['is_add_info_needed']:
            self.add_message((
                ChatRoles.USER.value,
                f"{self.agent_name}: {phase} prepared."
            ))
            self.state['requirements_overview'][key] = response['content']

            # update to next phase
            self.generation_phase += 1
        else:
            self.add_message((
                ChatRoles.USER.value,
                f"{self.agent_name}: {phase} has requested for additional information."
            ))
            self.request_additional_info(response)

    def requirements_overview(self, response: TaskOutput) -> None:
        """
        """
        
        if self.generation_phase == 0: # Project Overview
            self.update_requirements_overview("project_details", "Project Overview", response)
        elif self.generation_phase == 1: # Architecture
            self.update_requirements_overview("architecture", "Architecture", response)
        elif self.generation_phase == 2: # Folder Structure
            self.update_requirements_overview("folder_structure", "Folder Structure", response)
        elif self.generation_phase == 3: # Microservice Design
            self.update_requirements_overview("microservice_design", "Microservice Design", response)
        elif self.generation_phase == 4: # Tasks Breakdown
            self.update_requirements_overview("task_description", "Tasks Breakdown", response)
        elif self.generation_phase == 5: # Standards
            self.update_requirements_overview("standards", "Standards", response)
        elif self.generation_phase == 6: # Implementation Details
            self.update_requirements_overview("implementation_details", "Implementation Details", response)
        elif self.generation_phase == 7: # License Details
            self.update_requirements_overview("license_details", "License Details", response)

    def router(self, state: ArchitectState) -> str:
        """
        This method determines the next step based on the current state of the Architect agent.

        It checks the current state and returns the name of the next agent to be invoked. If 
        there is an error, it returns the last visited node. If the tasks are not separated, 
        it returns the tasks_seperation agent. If the requirements are not saved locally, 
        it returns the write_requirements agent. If none of these conditions are met, it 
        signifies the end of the process and returns "__end__".

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            str: The name of the next agent to be invoked or "__end__" if the process is complete.
        """

        print(f"----{self.agent_name}: Routing Graph----")

        if self.has_error:
            return self.last_visited_node
        elif self.mode == "generation":
            if not self.are_requirements_generated:
                return self.requirements
            elif not self.are_requirements_saved_to_local:
                return self.write_requirements
            elif not self.are_tasks_seperated:
                return self.tasks_seperation
        elif self.mode == "gather_info":
            if not self.is_additional_info_provided:
                return self.additional_info
        
        return self.state_update
    
    def update_state(self, state: ArchitectState) -> ArchitectState:
        """
        The method takes in a state, updates the current state of the object with the 
        provided state, and then returns the updated state.

        Args:
            state (any): The state to update the current state of the object with.

        Returns:
            any: The updated state of the object.
        """
        
        self.state = {**state}

        return {**self.state}
    
    def entry_node(self, state: ArchitectState) -> ArchitectState:
        """
        """
        print(f"----{self.agent_name}: Entry Point Triggered----")

        self.update_state(state)
        self.last_visited_node = self.entry

        if self.state['project_status'] == PStatus.INITIAL.value:
            self.mode = "generation"
        elif self.state["current_task"].task_status.value == Status.AWAITING.value:
            self.mode = "gather_info"

        return {**self.state}

    def requirements_node(self, state: ArchitectState) -> ArchitectState:
        """
        """
        print(f"----{self.agent_name}: Generating Requirements----")

        state['requirements_overview'] = {}
        self.generation_phase = 0
        self.update_state(state)
        self.last_visited_node = self.requirements

        self.add_message((
            ChatRoles.USER.value,
            f"{self.agent_name}: Started working on preparing the requirements overview."
        ))

        #0. Project Overview
        self.add_message((
            ChatRoles.USER.value,
            f"{self.agent_name}: Working on Project Overview."
        ))
        response: TaskOutput = self.project_overview_chain.invoke({
            "user_request": f"{self.state['user_request']}\n",
            "task_description": f"{self.state['current_task'].description}",
            "additional_information": f"{self.state['current_task'].additional_info}"
        })

        self.requirements_overview(response)
 
        # 1. Architecture
        self.add_message((
            ChatRoles.USER.value,
            f"{self.agent_name}: Working on Architecture."
        ))

        response: TaskOutput = self.architecture_chain.invoke({
            "project_overview": f"{self.state['requirements_overview']['project_details']}\n",
        })

        self.requirements_overview(response)

        # 2. Folder Structure
        self.add_message((
            ChatRoles.USER.value,
            f"{self.agent_name}: Working on Folder Structure."
        ))

        response: TaskOutput = self.folder_structure_chain.invoke({
            "project_overview": f"{self.state['requirements_overview']['project_details']}\n",
            "architecture": f"{self.state['requirements_overview']['architecture']}\n",
        })

        self.requirements_overview(response)

        # 3. Micro service Design
        self.add_message((
            ChatRoles.USER.value,
            f"{self.agent_name}: Working on Microservice Design."
        ))

        response: TaskOutput = self.microservice_design_chain.invoke({
            "project_overview": f"{self.state['requirements_overview']['project_details']}\n",
            "architecture": f"{self.state['requirements_overview']['architecture']}\n",
        })

        self.requirements_overview(response)

        # 4. Tasks Breakdown
        self.add_message((
            ChatRoles.USER.value,
            f"{self.agent_name}: Working on Tasks Breakdown."
        ))

        response: TaskOutput = self.tasks_breakdown_chain.invoke({
            "project_overview": f"{self.state['requirements_overview']['project_details']}\n",
            "architecture": f"{self.state['requirements_overview']['architecture']}\n",
            "microservice_design": f"{self.state['requirements_overview']['microservice_design']}\n",
        })

        self.requirements_overview(response)

        # 5. Standards
        self.add_message((
            ChatRoles.USER.value,
            f"{self.agent_name}: Working on Standards."
        ))

        response: TaskOutput = self.standards_chain.invoke({
            "user_request": f"{self.state['user_request']}\n",
            "task_description": f"{self.state['requirements_overview']['task_description']}\n",
        })

        self.requirements_overview(response)

        # 6. Implementation Details
        self.add_message((
            ChatRoles.USER.value,
            f"{self.agent_name}: Working on Implementation Details."
        ))

        response: TaskOutput = self.implementation_details_chain.invoke({
           "architecture": f"{self.state['requirements_overview']['architecture']}\n",
           "microservice_design": f"{self.state['requirements_overview']['microservice_design']}\n",
           "folder_structure": f"{self.state['requirements_overview']['folder_structure']}\n",
        })

        self.requirements_overview(response)

        # 7. License Details
        self.add_message((
            ChatRoles.USER.value,
            f"{self.agent_name}: Working on License Details."
        ))

        response: TaskOutput = self.license_legal_chain.invoke({
            "user_request": f"{self.state['user_request']}\n",
            "license_text": f"{self.state['license_text']}\n",
        })

        self.requirements_overview(response)

        self.are_requirements_generated = True
        self.are_tasks_seperated = True

        return {**self.state}

    def additional_information_node(self, state: ArchitectState) -> ArchitectState:
        """
        """
        
        print(f"----{self.agent_name}: Working on gathering additional information----")

        self.update_state(state)
        self.last_visited_node = self.additional_info

        self.add_message((
            ChatRoles.USER.value,
            f"{self.agent_name}: Started working on gathering the additional information."
        ))

        llm_response: QueryResult = self.additional_information_chain.invoke({
            "requirements_document": self.create_requirements_document(),
            "question": self.state['current_task'].question,
            "error_message": self.error_message
        })

        self.has_error = False
        self.error_message = ""
        
        try:
            required_keys = ["is_answer_found", "response_text"]
            missing_keys = [key for key in required_keys if key not in llm_response]

            if missing_keys:
                raise KeyError(f"Missing keys: {missing_keys} in the response. Try Again!")

            self.state["query_answered"] = llm_response['is_answer_found']
            
            response_text = llm_response['response_text'] if self.state["query_answered"] else "I don't have any additional information about the question."
            self.state["current_task"].additional_info = f"{self.state['current_task'].additional_info}, \nArchitect_Response:\n{response_text}"

            message_text = "Additional information has been successfully provided." if self.state["query_answered"] else "Unfortunately, I couldn't provide the additional information requested."

            self.add_message((
                ChatRoles.USER.value,
                message_text
            ))

            self.is_additional_info_provided = True
        except Exception as e:
            self.has_error = True
            self.error_message = f"An error occurred while processing the request: {str(e)}"

        return {**self.state}

    def write_requirements_to_local_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method is used to write the requirements overview to a local file. It updates 
        the state of the architect and sets the `are_requirements_saved_to_local` flag to True if 
        the requirements are successfully written.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """

        print(f"----{self.agent_name}: Writing requirements documents to local filesystem----")

        self.update_state(state)

        document = self.create_requirements_document()
        if len(document) < 0:
            self.has_error = True
            self.error_message = "ERROR: Found requirements document to be empty. Could not write it to file system."
            self.last_visited_node = self.requirements
            
            self.add_message((
                ChatRoles.USER.value,
                self.error_message,
            ))
        else:
            generated_code = document
            file_path = os.path.join(self.state['generated_project_path'], "docs/requirements.md")

            self.has_error, msg = CodeFileWriter.write_generated_code_to_file.invoke({"generated_code": generated_code, "file_path": file_path})
            
            # if self.has_error:
            #     self.error_message = msg
            #     self.last_visited_node = self.requirements_and_additional_context
            # else:
            self.has_error = False
            self.error_message = ""
            self.last_visited_node = self.write_requirements
            self.are_requirements_saved_to_local = True

            self.add_message((
                ChatRoles.USER.value,
                msg
            ))


        return {**self.state}

    def tasks_seperation_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method separates tasks from the requirements document and creates a list of tasks
        and updates the state.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """

        print(f"----{self.agent_name}: Working on Tasks Seperation----")

        self.last_visited_node = self.tasks_seperation
        self.update_state(state)

        task_seperation_solution = self.task_seperation_chain.invoke({
            "tasks": self.state['tasks'],
            "error_message": self.error_message
        })
        
        self.has_error = False
        self.error_message = ""

        try:
            tasks = task_seperation_solution['tasks']

            if not isinstance(tasks, list):
                raise TypeError(f"Expected 'tasks' to be of type list but received {type(tasks).__name__}.")
          
            if not tasks:
                raise ValueError("The 'tasks' list in the received in previous response is empty.")
            
            self.state['tasks'] = self.create_tasks(tasks)

            self.are_tasks_seperated = True
            self.add_message((
                ChatRoles.USER.value,
               "The tasks list has been successfully generated. You may now continue with your work on these tasks."
            ))

        except ValueError as ve:
            self.has_error = True
            self.error_message = f"ValueError occurred: {ve}"

            self.add_message((
                ChatRoles.USER.value,
                self.error_message
            ))

        except TypeError as te:
            self.has_error = True
            self.error_message = f"TypeError occurred: {te}"

            self.add_message((
                ChatRoles.USER.value,
                self.error_message
            ))
            
        except Exception as e:
            self.has_error = True
            self.error_message = f"An unexpected error occurred: {e}"

            self.add_message((
                ChatRoles.USER.value,
                self.error_message
            ))           

        return {**self.state}
