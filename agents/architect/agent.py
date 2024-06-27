"""Architect Agent

This module contains the ArchitectAgent class which is responsible for 
managing the state of the Architect agent, processing user inputs, and 
generating appropriate responses.
"""

from langgraph.prebuilt import ToolExecutor

from langchain_core.runnables.base import RunnableSequence

from prompts.architect import ArchitectPrompts

from models.constants import Status
from models.constants import ChatRoles

from models.models import Task

from models.architect import TasksList
from models.architect import QueryResult
from models.architect import RequirementsDoc

from agents.architect.state import ArchitectState

from tools.fs import FS

import pprint as pp
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
    architect: str = "architect"
    write_requirements: str = "write_requirements"
    tasks_seperation: str = "tasks_seperation"

    # local state of this class which is not exposed
    # to the graph state
    hasError: bool
    areTasksSeperated: bool
    is_requirements_written_to_local: bool

    previous_output: any
    missing_keys: list[str]
    expected_keys: list[str]
    tasks: str
    last_visited_node: str
    iteration: int
    recursive_limit: int

    # tools used by this agent
    tools: ToolExecutor

    # local variables of this class
    state: ArchitectState = ArchitectState()
    requirements_genetation_chain: RunnableSequence
    requirements_genetation_error_chain: RunnableSequence
    additional_information_chain: RunnableSequence
    task_seperation_chain: RunnableSequence

    def __init__(self, llm) -> None:
        """
        Initializes the ArchitectAgent with a given Language Learning Model
        (llm) and sets up the architect chain.
        """

        self.hasError = False
        self.areTasksSeperated = False
        self.is_requirements_written_to_local = False
        self.previous_output = ""
        self.missing_keys = []
        self.expected_keys = []
        self.tasks = ""

        self.llm = llm
        self.tools = ToolExecutor([FS.write_generated_code_to_file])

        # This chain is used initially when the project requirements need to be generated
        self.requirements_genetation_chain = (
            {
                "user_request": lambda x: x["user_request"],
                "user_requested_standards": lambda x: x["user_requested_standards"]
            }
            | ArchitectPrompts().requirements_generation_prompt()
            | self.llm.with_structured_output(RequirementsDoc, include_raw=True)
        )

        self.requirements_genetation_error_chain = (
            {
                "previous_output": lambda x: x["previous_output"],
                "missing_fields": lambda x: x["missing_fields"],
                "user_request": lambda x: x["user_request"],
                "user_requested_standards": lambda x: x["user_requested_standards"]
            }
            | ArchitectPrompts().requirements_generation_error_prompt()
            | self.llm.with_structured_output(RequirementsDoc, include_raw=True)
        )

        # This chain is used when team member requests for additional information to complete 
        # the task
        self.additional_information_chain = (
            {
                "requirements_document": lambda x: x["requirements_overview"],
                "current_task": lambda x: x["current_task"],
                "question": lambda x: x["question"]
            }
            | ArchitectPrompts().additional_info_prompt()
            | self.llm.with_structured_output(QueryResult, include_raw=True)
        )

        self.task_seperation_chain = (
            {
                "requirements_document": lambda x: x["requirements_document"],
                "tasks": lambda x : x["tasks"],
            }
            | ArchitectPrompts().task_seperation_prompt()
            | self.llm.with_structured_output(TasksList, include_raw=True)
        )

    def create_tasks(self, tasks: str) -> list[Task]:
        """
        """

        t_list = ast.literal_eval(tasks)
        tasks_list: list[Task] = []

        for ti in t_list:
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

    def node(self, state: ArchitectState) -> ArchitectState:
        """
        Processes the current state of the Architect agent, updates the state 
        based on the user input, and returns the updated state.
        """
        self.state = state
        self.last_visited_node = self.architect
        self.expected_keys = []

        if self.state['project_state'] == Status.NEW:
            if not self.hasError:
                architect_solution = self.requirements_genetation_chain.invoke({
                    "user_request": self.state['user_request'],
                    "user_requested_standards": self.state["user_requested_standards"]
                })

                self.add_message((
                    ChatRoles.USER.value,
                    "Started working on preparing the requirements and tasks for team members"
                ))
            else:
                self.hasError = False
                self.previous_output = ""
                self.missing_keys = []
                self.expected_keys = []

                architect_solution = self.requirements_genetation_error_chain.invoke({
                    "previous_output": self.previous_output,
                    "missing_fields": self.missing_keys,
                    "user_request": self.state['user_request'],
                    "user_requested_standards": self.state["user_requested_standards"]
                })
            
            self.expected_keys = [item for item in RequirementsDoc.__annotations__ if item != "description"]
        elif self.state['current_task'].task_status == Status.AWAITING:
            architect_solution = self.additional_information_chain.invoke({
                "current_task": self.state['current_task'].description,
                "requirements_overview": self.state["requirements_overview"],
                "question": self.state['current_task'].question
            })

            self.expected_keys = [item for item in QueryResult.__annotations__ if item != "description"]

        if ('parsing_error' in architect_solution) and architect_solution['parsing_error']:
            self.hasError = True
            self.previous_output = architect_solution

            self.add_message((
                ChatRoles.USER.value,
                f"ERROR: parsing your output! Be sure to invoke the tool. Output: {self.previous_output}."
                f" \n Parse error: {architect_solution['parsing_error']}"
            ))
        else:
            for key in self.expected_keys:
                if key not in architect_solution['parsed']:
                    self.missing_keys.append(key)

            if len(self.missing_keys) > 0:
                self.hasError = True
                self.previous_output = architect_solution

                self.add_message((
                    ChatRoles.USER.value,
                    f"ERROR: Output was not structured properly. Expected keys: {self.expected_keys}, "
                    f"Missing Keys: {self.missing_keys}."        
                ))
            elif self.state['project_state'] == Status.NEW:

                self.state["project_name"] = architect_solution['parsed']['project_name']
                self.state["requirements_overview"] = architect_solution['parsed']['well_documented']
                self.state["project_folder_strucutre"] = architect_solution['parsed']['project_folder_structure']
                self.tasks = architect_solution['parsed']['tasks']
                self.is_requirements_written_to_local = False

                self.add_message((
                    ChatRoles.AI.value,
                    "The project implementation has been successfully initiated. Please proceed "
                    "with the next steps as per the requirements documents.",
                ))

                self.add_message((
                    ChatRoles.USER.value,
                    "Write requirements document to local file system."
                ))
            elif self.state['current_task'].task_status == Status.AWAITING:
                
                if architect_solution['parsed']['is_answer_found']:
                    self.state["current_task"].additional_info = architect_solution['parsed']['response_text']

                    self.add_message((
                        ChatRoles.AI.value,
                        "Additional information has been successfully provided. You may now proceed "
                        "with task completion."
                    ))
                else:
                    self.add_message((
                        ChatRoles.AI.value,
                        "Unfortunately, I couldn't provide the additional information requested. "
                        "Please assess if you can complete the task with the existing details, or "
                        "consider abandoning the task if necessary."
                    ))

        return {**self.state}
    
    def write_requirements_to_local(self, state: ArchitectState) -> ArchitectState:
        """
        """
        self.last_visited_node = self.write_requirements
        self.state = state
        self.expected_keys = []

        if len(self.state['requirements_overview']) < 0:
            self.add_message((
                ChatRoles.USER.value,
                "ERROR: Found requirements documents to empty. Could not write it to file system."
            ))
        else:
            generated_code = self.state['requirements_overview']
            project_path = os.getenv("PROJECT_PATH", "/opt/output")
            file_path = os.path.join(project_path, "docs/requirements.md")

            # action= ToolInvocation(
            #     tool= "write_generated_code_to_file",
            #     tool_input={"generated_code": generated_code, "file_path": file_path}
            # )
            
            # msg = self.tools.invoke(action)

            isError, msg = FS.write_generated_code_to_file.invoke({"generated_code": generated_code, "file_path": file_path})
            self.add_message((
                ChatRoles.USER.value,
                msg
            ))

            self.is_requirements_written_to_local = True


        return {**self.state}

    def tasks_seperation_node(self, state: ArchitectState) -> ArchitectState:
        """
        """

        self.last_visited_node = self.tasks_seperation
        self.state = state
        self.expected_keys = []

        task_seperation_solution = self.task_seperation_chain.invoke({
            "requirements_document": self.state['requirements_overview'],
            "tasks": self.tasks
        })
        
        self.hasError = False
        self.previous_output = ""
        self.missing_keys = []
        self.expected_keys = [item for item in TasksList.__annotations__ if item != "description"]
        
        if ('parsing_error' in task_seperation_solution) and task_seperation_solution['parsing_error']:
            self.hasError = True
            self.previous_output = task_seperation_solution

            self.add_message((
                ChatRoles.USER.value,
                f"ERROR: parsing your output! Be sure to invoke the tool. Output: {self.previous_output}."
                f" \n Parse error: {task_seperation_solution['parsing_error']}"
            ))
        else:
            for key in self.expected_keys:
                if key not in task_seperation_solution['parsed']:
                    self.missing_keys.append(key)

            if len(self.missing_keys) > 0:
                self.hasError = True
                self.previous_output = task_seperation_solution

                self.add_message((
                    ChatRoles.USER.value,
                    f"ERROR: Output was not structured properly. Expected keys: {self.expected_keys}, "
                    f"Missing Keys: {self.missing_keys}."        
                ))   
            else:
                self.hasError = False
                self.areTasksSeperated = True
                self.state['tasks'] = self.create_tasks(task_seperation_solution['parsed']['tasks'])

                self.add_message((
                    ChatRoles.USER.value,
                    "Tasks list has been created. Please proceed working on it."
                ))
        
        return {**self.state}

    def router(self, state: ArchitectState) -> str:
        """
        Determines the next step based on the current state of the Architect 
        agent and returns the name of the next agent or "__end__".
        """

        if self.hasError:
            return self.last_visited_node
        elif not self.areTasksSeperated:
            return self.tasks_seperation
        elif not self.is_requirements_written_to_local:
            return self.write_requirements
        
        return "__end__"