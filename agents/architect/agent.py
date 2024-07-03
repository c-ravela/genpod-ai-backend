"""Architect Agent

This module contains the ArchitectAgent class which is responsible for 
managing the state of the Architect agent, processing user inputs, and 
generating appropriate responses.
"""

from langgraph.prebuilt import ToolExecutor

from langchain_core.runnables.base import RunnableSequence

from prompts.architect import ArchitectPrompts

from models.constants import PStatus
from models.constants import Status
from models.constants import ChatRoles

from models.models import Task

from models.architect import TasksList
from models.architect import QueryResult
from models.architect import RequirementsDoc

from agents.architect.state import ArchitectState

from tools.code import CodeFileWriter

import os
import ast

class ArchitectAgent:
    """
    ArchitectAgent Class

    This class represents the Architect agent. It maintains the state of the
    agent, processes user inputs, and generates appropriate responses. It uses 
    a chain of tools to parse the user input and generate a structured output.
    """

    # names of the graph node
    requirements_and_additional_context: str = "requirements_and_additional_context"
    write_requirements: str = "write_requirements"
    tasks_seperation: str = "tasks_seperation"
    state_update: str = "state_update"

    # local state of this class which is not exposed
    # to the graph state
    hasError: bool
    areTasksSeperated: bool
    areRequirementsSavedLocally: bool

    tasks: str
    last_visited_node: str

    missing_keys: list[str]
    expected_keys: list[str]

    error_message: str
    previous_output: any

    # tools used by this agent
    tools: ToolExecutor

    state: ArchitectState = ArchitectState()
    prompts: ArchitectPrompts = ArchitectPrompts()

    requirements_genetation_chain: RunnableSequence
    additional_information_chain: RunnableSequence
    task_seperation_chain: RunnableSequence

    def __init__(self, llm) -> None:
        """
        Initializes the ArchitectAgent with a given Language Learning Model
        (llm) and sets up the architect chain.
        """

        self.hasError = False
        self.areTasksSeperated = False
        self.areRequirementsSavedLocally = False
        
        self.tasks = ""
        self.last_visited_node = self.requirements_and_additional_context # entry point node

        self.missing_keys = []
        self.expected_keys = []

        self.error_message = ""
        self.previous_output = ""

        self.llm = llm
        self.tools = ToolExecutor([CodeFileWriter.write_generated_code_to_file])

        # This chain is used initially when the project requirements need to be generated
        self.requirements_genetation_chain = (
            {
                "user_request": lambda x: x["user_request"],
                "user_requested_standards": lambda x: x["user_requested_standards"],
                "error_message": lambda x: x["error_message"]
            }
            | self.prompts.requirements_generation_prompt()
            | self.llm.with_structured_output(RequirementsDoc, include_raw=True)
        )
        
        # This chain is used when team member requests for additional information to complete 
        # the task
        self.additional_information_chain = (
            {
                "requirements_document": lambda x: x["requirements_overview"],
                "current_task": lambda x: x["current_task"],
                "question": lambda x: x["question"],
                "error_message": lambda x: x["error_message"]
            }
            | self.prompts.additional_info_prompt()
            | self.llm.with_structured_output(QueryResult, include_raw=True)
        )

        # This chain is used when we need to create a list of tasks from the markdown formatted
        # tasks
        self.task_seperation_chain = (
            {
                "requirements_document": lambda x: x["requirements_document"],
                "tasks": lambda x : x["tasks"],
                "error_message": lambda x: x["error_message"]
            }
            | self.prompts.task_seperation_prompt()
            | self.llm.with_structured_output(TasksList, include_raw=True)
        )

    def create_tasks(self, tasks: str) -> list[Task]:
        """
        This method is used to create a list of Task objects from a string representation of a list.

        Args:
            tasks (str): A string representation of a list where each element is a description of a 
            task.

        Returns:
            list[Task]: A list of Task objects with the description set from the input and the status 
            set as NEW.
        """

        print("----Architect: Creating List of Tasks----")
        ts_list = ast.literal_eval(tasks)
        tasks_list: list[Task] = []

        for ti in ts_list:
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

        Returns:
            ArchitectState: The updated state with the new message added to the 
            messages field.
        """

        self.state['messages'] += [message]

    def requirements_and_additional_context_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method processes the current state of the Architect agent and updates it based on the user input.
        
        It handles two main states: 'NEW' and 'AWAITING'. 

        In the 'NEW' state, it invokes the requirements generation chain if there are no errors, or the requirements generation error chain if there are errors. 
        It then updates the state with the response from the invoked chain.

        In the 'AWAITING' state, it invokes the additional information chain and updates the state with the response from the invoked chain.

        If there are any parsing errors in the response from the invoked chain, it sets the error flag and stores the error message. 
        If the output is not structured properly, it sets the error flag and stores the missing keys.

        Finally, it returns the updated state.

        Parameters:
            state (ArchitectState): The current state of the Architect agent.

        Returns:
            ArchitectState: The updated state of the Architect agent.
        """

        self.update_state(state)
        self.last_visited_node = self.requirements_and_additional_context
        self.expected_keys = []

        if self.state['project_status'] == PStatus.INITIAL.value:
            self.add_message((
                ChatRoles.USER.value,
                "Started working on preparing the requirements and tasks for team members"
            ))
            print("----Architect: Working of requiements documents----")
            print("ReqDoc: ", self.error_message)
            llm_response = self.requirements_genetation_chain.invoke({
                "user_request": f"{self.state['user_request']}\n {self.state['current_task'].description}",
                "user_requested_standards": f"{self.state["user_requested_standards"]} \n {self.state['current_task'].additional_info}",
                "error_message": self.error_message
            })

            self.expected_keys = [item for item in RequirementsDoc.__annotations__ if item != "description"]
        elif self.state['current_task'].task_status.value == Status.AWAITING.value:
            print("----Architect: Working on gathering additional information----")
            print("Additional: ", self.error_message)

            self.add_message((
                ChatRoles.USER.value,
                "Started working on gathering the additional information for team member."
            ))
            llm_response = self.additional_information_chain.invoke({
                "current_task": self.state['current_task'].description,
                "requirements_overview": self.state["requirements_overview"],
                "question": self.state['current_task'].question,
                "error_message": self.error_message
            })

            self.expected_keys = [item for item in QueryResult.__annotations__ if item != "description"]

        if self.hasError:
            self.hasError = False
            self.previous_output = ""
            self.missing_keys = []
            self.error_message = ""

        if ('parsing_error' in llm_response) and llm_response['parsing_error']:
            self.hasError = True
            self.previous_output = llm_response

            self.error_message = f"ERROR: parsing your output! Be sure to invoke the tool. Output: {self.previous_output}.\n Parse error: {llm_response['parsing_error']}."
            
            self.add_message((
                ChatRoles.USER.value,
                self.error_message
            ))
        else:
            for key in self.expected_keys:
                if key not in llm_response['parsed']:
                    self.missing_keys.append(key)

            if len(self.missing_keys) > 0:
                self.hasError = True
                self.previous_output = llm_response

                self.error_message = f"ERROR: Output was not structured properly. Expected keys: {self.expected_keys}, " f"Missing Keys: {self.missing_keys}."        

                self.add_message((
                    ChatRoles.USER.value,
                    self.error_message
                ))
            elif self.state['project_status'] == PStatus.INITIAL.value:

                self.state["current_task"].task_status = Status.DONE
                self.state["project_name"] = llm_response['parsed']['project_name']
                self.state["requirements_overview"] = llm_response['parsed']['well_documented']
                self.state["project_folder_strucutre"] = llm_response['parsed']['project_folder_structure']
                self.tasks = llm_response['parsed']['tasks']
                self.state["query_answered"] = False

                self.add_message((
                    ChatRoles.AI.value,
                    "The project implementation has been successfully initiated. Please proceed "
                    "with the next steps as per the requirements documents.",
                ))

            elif self.state['current_task'].task_status.value == Status.AWAITING.value:
                
                if llm_response['parsed']['is_answer_found']:
                    self.state["query_answered"] = True
                    self.state["current_task"].additional_info = f"{self.state["current_task"].additional_info}, \nArchitect_Response:\n{llm_response['parsed']['response_text']}"

                    self.add_message((
                        ChatRoles.AI.value,
                        "Additional information has been successfully provided. You may now proceed "
                        "with task completion."
                    ))
                else:
                    self.state["query_answered"] = False
                    self.state["current_task"].additional_info = f"{self.state["current_task"].additional_info}, \nArchitect_Response:\nI don't have any additional information about the question."

                    self.add_message((
                        ChatRoles.AI.value,
                        "Unfortunately, I couldn't provide the additional information requested. "
                        "Please assess if you can complete the task with the existing details, or "
                        "consider abandoning the task if necessary."
                    ))
        
        return {**self.state}
    
    def write_requirements_to_local_node(self, state: ArchitectState) -> ArchitectState:
        """
        This method is used to write the requirements overview to a local file. It updates 
        the state of the architect and sets the `areRequirementsSavedLocally` flag to True if 
        the requirements are successfully written.

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """

        print("----Architect: Writing requirements documents to local filesystem----")

        self.update_state(state)

        if len(self.state['requirements_overview']) < 0:
            self.add_message((
                ChatRoles.USER.value,
                "ERROR: Found requirements document to be empty. Could not write it to file system."
            ))
        else:
            generated_code = self.state['requirements_overview']
            file_path = os.path.join(self.state['generated_project_path'], "docs/requirements.md")

            self.hasError, msg = CodeFileWriter.write_generated_code_to_file.invoke({"generated_code": generated_code, "file_path": file_path})
            
            if self.hasError:
                self.error_message = msg
                self.last_visited_node = self.requirements_and_additional_context
            else:
                self.hasError = False
                self.error_message = ""
                self.last_visited_node = self.write_requirements
                self.areRequirementsSavedLocally = True

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

        print("----Architect: Working on tasks seperation----")

        self.last_visited_node = self.tasks_seperation
        self.update_state(state)

        print("Tasks: ", self.error_message)
        task_seperation_solution = self.task_seperation_chain.invoke({
            "requirements_document": self.state['requirements_overview'],
            "tasks": self.tasks,
            "error_message": self.error_message
        })
        
        self.hasError = False
        self.previous_output = ""
        self.missing_keys = []
        self.expected_keys = [item for item in TasksList.__annotations__ if item != "description"]
        self.error_message = ""
        
        if ('parsing_error' in task_seperation_solution) and task_seperation_solution['parsing_error']:
            self.hasError = True
            self.previous_output = task_seperation_solution
            self.error_message = f"ERROR: parsing your output! Be sure to invoke the tool. Output: {self.previous_output}."
            f" \n Parse error: {task_seperation_solution['parsing_error']}"

            self.add_message((
                ChatRoles.USER.value,
                self.error_message
            ))
        else:
            for key in self.expected_keys:
                if key not in task_seperation_solution['parsed']:
                    self.missing_keys.append(key)

            if len(self.missing_keys) > 0:
                self.hasError = True
                self.previous_output = task_seperation_solution

                self.error_message = f"ERROR: Output was not structured properly. Expected keys: {self.expected_keys}, "
                f"Missing Keys: {self.missing_keys}."        

                self.add_message((
                    ChatRoles.USER.value,
                    self.error_message
                ))   
            else:
                self.hasError = False
                self.missing_keys = []
                self.expected_keys = []
                self.previous_output = ""
                self.error_message = ""

                try:
                    self.state['tasks'] = self.create_tasks(task_seperation_solution['parsed']['tasks'])

                    if len(self.state['tasks']) < 1:
                        raise ValueError(f"'tasks' list is empty.")
                    
                    self.add_message((
                        ChatRoles.USER.value,
                        "Tasks list has been created. Please proceed working on it."
                    ))

                    self.areTasksSeperated = True
                except Exception as e:

                    self.hasError = True
                    self.error_message = f"ERROR: PARSER ERROR or VALUE ERROR has encountered! 'tasks' is not a list or received an empty list. Got exception {e}"

                    self.add_message((
                        ChatRoles.USER.value,
                        self.error_message
                    ))

        return {**self.state}

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

        if self.hasError:
            return self.last_visited_node
        elif not self.areRequirementsSavedLocally:
            return self.write_requirements
        elif not self.areTasksSeperated:
            return self.tasks_seperation
        
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
    