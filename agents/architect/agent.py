"""Architect Agent

This module contains the ArchitectAgent class which is responsible for 
managing the state of the Architect agent, processing user inputs, and 
generating appropriate responses.
"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables.base import RunnableSequence

from prompts.architect import ArchitectPrompts

from models.models import Task

from models.constants import Status
from models.constants import ChatRoles
from models.architect import QueryResult
from models.architect import RequirementsDoc

from agents.architect.state import ArchitectState

class ArchitectAgent:
    """
    ArchitectAgent Class

    This class represents the Architect agent. It maintains the state of the
    agent, processes user inputs, and generates appropriate responses. It uses 
    a chain of tools to parse the user input and generate a structured output.
    """

    name: str = "architect"
    state: ArchitectState = ArchitectState()
    requirements_genetation_chain: RunnableSequence
    additional_information_chain: RunnableSequence

    def __init__(self, llm) -> None:
        """
        Initializes the ArchitectAgent with a given Language Learning Model
        (llm) and sets up the architect chain.
        """

        self.llm = llm
        
        # This chain is used initially when the project requirements need to be generated
        self.requirements_genetation_chain = (
            {
                "user_request": lambda x: x["user_request"],
                "user_requested_standards": lambda x: x["user_requested_standards"]
            }
            | ArchitectPrompts.requirements_generation_prompt(RequirementsDoc)
            | self.llm.with_structured_output(RequirementsDoc, include_raw=True)
            | JsonOutputParser()
        )

        # This chain is used when team member requests for additional information to complete 
        # the task
        self.additional_information_chain = (
            {
                "chat_history": lambda x: x["messages"],
                "requirements_document": lambda x: x["requirements_overview"],
                "current_task": lambda x: x["current_task"],
                "question": lambda x: x["question"]
            }
            | ArchitectPrompts.additional_info_prompt(QueryResult)
            | self.llm.with_structured_output(QueryResult, include_raw=True)
            | JsonOutputParser()
        )

    def toggle_error(self) -> None:
        """
        Toggles the error field in the state. If the error is True, it becomes 
        False and vice versa.

        Returns:
            ArchitectState: The updated state with the toggled error field.
        """

        self.state['error'] = not self.state['error']

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

        if self.state['project_state'] == Status.NEW:
            architect_solution = self.requirements_genetation_chain.invoke({
                "user_request": self.state['user_request'],
                "user_requested_standards": self.state["user_requested_standards"]
            })

            self.state["project_name"] = architect_solution['parsed']['project_name']
            self.state["requirements_overview"] = architect_solution['parsed']['well_documented']
            self.state["project_folder_strucutre"] = architect_solution['parsed']['project_folder_strucutre']
            self.state["tasks"] = architect_solution['parsed']['tasks']

            self.add_message((
                ChatRoles.AI.value,
                "The project implementation has been successfully initiated. Please proceed "
                "with the next steps as per the requirements documents.",
            ))

        elif self.state['current_task'].task_status == Status.AWAITING:
            architect_solution = self.additional_information_chain.invoke({
                "chat_history": self.state['messages'],
                "current_task": self.state['current_task'].description,
                "requirements_document": self.state["requirements_overview"],
                "question": self.state['current_task'].question
            })

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
    
    def router(self, state: ArchitectState) -> str:
        """
        Determines the next step based on the current state of the Architect 
        agent and returns the name of the next agent or "__end__".
        """

        return "__end__"
