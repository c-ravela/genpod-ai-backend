from langchain_core.output_parsers import JsonOutputParser
from agents.planner.planner_state import PlannerState
from agents.planner.planner_prompt import PlannerPrompts
from models.models import Task
from models.constants import Status
import ast
from agents.planner.planner_models import BacklogList
from pydantic import ValidationError
import json
from typing import List
from pprint import pprint

class PlannerAgent():
    def __init__(self, llm):
        
        self.llm = llm
        
        # backlog planner for each deliverable chain
        self.backlog_plan = PlannerPrompts.backlog_planner_prompt | self.llm
        
        # detailed requirements generator chain
        self.detailed_requirements = PlannerPrompts.detailed_requirements_prompt | self.llm

        # State to maintain when responding back to supervisor
        self.state = {}
        
        self.current_task : Task = None

        self.error_count = 0
        self.max_retries = 3
        self.error_messages = []
        self.backlog_requirements = {}
    
    def new_deliverable_check(self, state: PlannerState):
        # self.current_task = {x:config['configurable'][x] for x in ['description','task_status','additional_info','question']}
        # self.current_task = state.new_task
        # if config['configurable']['task_status'] == Status.NEW.value:
        if state['current_task'].task_status.value == Status.NEW.value:
            return "backlog_planner"
        else:
            return "requirements_developer"

    def backlog_planner(self, state: PlannerState):
        while(True):
            try:
                print(f"----Working on building backlogs for the deliverable----\n{state['current_task'].description}")
                generated_backlogs = self.backlog_plan.invoke({"deliverable":state['current_task'].description, "context":state['current_task'].additional_info, "feedback":self.error_messages})
                backlogs_list = ast.literal_eval(generated_backlogs.content)
                # backlogs_list = self.parse_backlog_tasks(generated_backlogs.content)
                # Validate the response using Pydantic
                validated_backlogs = BacklogList(backlogs=backlogs_list)
                
                self.error_count = 0
                self.error_messages = []

                # Update the state with the validated backlogs
                state['deliverable'] = state['current_task'].description
                state['backlogs'] = validated_backlogs.backlogs

                # Extend the deliverable_backlog_map with the new backlogs
                state['deliverable_backlog_map'] = {state['deliverable']: [wp for wp in state['backlogs']]}

                return {**state}
            
            except (ValidationError, ValueError, SyntaxError) as e:
                self.error_count += 1
                error_message = f"Error generating backlogs: {str(e)}"
                print(error_message)
                self.error_messages.append(error_message)
                
                if self.error_count >= self.max_retries:
                    print("Max retries reached. Halting")
                    self.error_count = 0
                    return {**state}

    def requirements_developer(self, state: PlannerState):
        for backlog in state['deliverable_backlog_map'][state['current_task'].description]:
            while(True):
                try:
                    print(f"----Now Working on Generating detailed requirements for the backlog----\n{backlog}")
                    response = self.detailed_requirements.invoke({"backlog":backlog, "deliverable":state['deliverable'], "context":state['current_task'].additional_info, "feedback":self.error_messages})

                    # Let's clean the response to remove json prefix that llm sometimes appends to the actual text
                    # Strip whitespace from the beginning and end
                    cleaned_response = response.content.strip()
                    
                    # Check if the text starts with ```json and ends with ```
                    if cleaned_response.startswith('```json') and cleaned_response.endswith('```'):
                        # Remove the ```json prefix and ``` suffix
                        cleaned_json = cleaned_response.removeprefix('```json').removesuffix('```').strip()
                    else:
                        # If not enclosed in code blocks, use the text as is
                        cleaned_json = cleaned_response
                    parsed_response = json.loads(cleaned_json)
                    if "question" in parsed_response.keys():
                        print(f"----Awaiting for additional information on----\n{parsed_response['question']}")
                        state['current_task'].task_status = Status.AWAITING
                        state['current_task'].question = parsed_response['question']
                        return {**state}
                    elif "description" in parsed_response.keys():
                        print("----Generated Detailed requirements in JSON format for the backlog----\n")
                        pprint(parsed_response)
                        self.backlog_requirements[backlog] = parsed_response
                        self.error_count = 0
                        self.error_messages = []
                        break
                except Exception as e:
                    print(f"Error parsing response for backlog: {backlog}, {e}")
                    self.error_count += 1
                    error_message = f"Error in generated detailed requirements format: {str(e)}, I'm using python json.loads() to convert json to dictionary so take that into consideration."
                    print(error_message)
                    self.error_messages.append(error_message)
                    
                    if self.error_count >= self.max_retries:
                        print("Max retries reached. Halting")
                        self.error_count = 0
                        return {**state}
        """Uncomment the below line to call coder on each workpackage created for the deliverable. Currently coder is not implemented yet so we will try to build workpackages for eacg deliverable using the Done mode."""
        # state['current_task'].task_status = Status.INPROGRESS
        state['current_task'].task_status = Status.DONE
        return {**state}

    def generate_response(self, state: PlannerState):
        if state['current_task'].task_status.value == Status.DONE.value:
            # ----when calling Coder----
            # response = Task(description="All Backlogs for the deliverable is successfully generated proceed further", task_status=Status.INPROGRESS.value, additional_info='',question='')
            # ----When recursively calling planner on each deliverable----
            response = Task(description="All Backlogs for the deliverable is successfully generated proceed further", task_status=Status.DONE.value, additional_info=state['current_task'].additional_info,question='')
        elif state['current_task'].task_status.value == Status.AWAITING.value:
            response = state['current_task']
        else:
            response = Task(description=state['current_task'].description, task_status=Status.ABANDONED.value, additional_info=state['current_task'].additional_info, question=state['current_task'].question)

        if state['response'] is None:
            state["response"] = [response]
        else:
            state["response"].append(response)
        return {**state}

    def update_state(self, state: PlannerState):
        self.state = {**state}
        return {**state}
    
    def parse_backlog_tasks(self, response: str) -> List[str]:
        import re
        # Split the response into lines
        lines = response.split('\n')
        
        # Extract tasks using regex
        tasks = []
        for line in lines:
            # Match lines that start with numbers or bullet points
            match = re.match(r'^(\d+\.|\*|\-)\s*\*{0,2}([^:]+)(:|\*{0,2})', line.strip())
            if match:
                task = match.group(2).strip()
                tasks.append(task)
        
        return tasks
