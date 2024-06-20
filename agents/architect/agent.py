"""
Architect agent
"""

from langchain_core.output_parsers import JsonOutputParser

from prompts.architect import architect_prompt

from agents.architect.model import TaskState
from agents.architect.model import RequirementsDoc

from agents.architect.state import add_message
from agents.architect.state import toggle_error
from agents.architect.state import ArchitectState

import ast

class ArchitectAgent:
    """
    """
    name = "architect"

    def __init__(self, llm) -> None:
        self.llm = llm
        
        # architect chain
        self.architect_chain = (
            architect_prompt
            | self.llm.with_structured_output(RequirementsDoc, include_raw=True)
            | JsonOutputParser()
        )

    def node(self, state: ArchitectState) -> ArchitectState:
        """
        """
        expected_keys = []
        architect_solution = {}

        if state['error']:
            state = toggle_error(state)
        
        if state['project_state'] == TaskState.NEW.value:
            print(state)
            architect_solution = self.architect_chain.invoke(state['messages'])
            expected_keys = [item for item in RequirementsDoc.__annotations__ if item != "description"]
        
        missing_keys = [] 
        for key in expected_keys:
            if key not in architect_solution['parsed']:
                missing_keys.append(key)

        if (state['project_state'] == TaskState.NEW.value) and architect_solution['parsing_error']:
            raw_output = architect_solution['raw']
            error = architect_solution['parsing_error']

            state = toggle_error(state)
            state = add_message(state, (
                "user",
                f"ERROR: parsing your output! Be sure to invoke the tool. Output: {raw_output}. \n Parse error: {error}"
            ))
        elif missing_keys:
            state = toggle_error(state)
            state = add_message(state, (
                    "user",
                    f"ERROR: Now, try again. Invoke the RequirementsDoc tool to structure the output with a project_name, well_documented, tasks, project_folder_structure, next_task and call_next, you missed {missing_keys} in your previous response",        
            ))
        elif state['project_state'] == TaskState.AWAITING.value:
            state['current_task'] = state['tasks'].pop(0)
            
            if state['current_task'] is None:
                state['project_state'] = TaskState.COMPLETED.value
            else:
                state['project_state'] = TaskState.INPROGRESS.value

            state = add_message(state, (
                "assistant",
                f"A new task: '{state['current_task']}' has been assigned! Please check the details and start working on it."
            ))
        else:
            state['requirements_overview'] = architect_solution['parsed']['well_documented']
            state['project_name'] = architect_solution['parsed']['project_name']
            state['project_folder_structure'] = architect_solution['parsed']['project_folder_structure']
            state['tasks'] = ast.literal_eval(architect_solution['parsed']['tasks'])
            state['current_task'] = state['tasks'].pop(0)
            state['curr_task_status'] = TaskState.NEW.value

            state = add_message(state, (
                "assistant",
                "Well documented requirements are present now. see what task needs to be completed and please do that now.",
            )) 
        
        return state
    
    def router(self, state: ArchitectState) -> str:
        """
        """

        if state['error'] or (state['project_state'] == TaskState.AWAITING.value):
            return self.name
    
        if state['project_state'] == TaskState.COMPLETED.value:
            return "__end__"
        
        return "__end__"

