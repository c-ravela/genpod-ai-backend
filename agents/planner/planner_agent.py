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


class PlannerAgent():
    def __init__(self, llm):
        
        self.llm = llm
        
        # backlog planner for each deliverable chain
        self.backlog_plan = PlannerPrompts.backlog_planner_prompt | self.llm
        
        # detailed requirements generator chain
        self.detailed_requirements = PlannerPrompts.detailed_requirements_prompt | self.llm | JsonOutputParser()

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
        if self.current_task.task_status.value == Status.NEW.value:
            return "backlog_planner"
        else:
            return "requirements_developer"

    def backlog_planner(self, state: PlannerState):
        while(True):
            try:
                generated_backlogs = self.backlog_plan.invoke({"deliverable":self.current_task.description, "context":self.current_task.additional_info, "feedback":self.error_messages})
                backlogs_list = ast.literal_eval(generated_backlogs.content)
                # backlogs_list = self.parse_backlog_tasks(generated_backlogs.content)
                # Validate the response using Pydantic
                validated_backlogs = BacklogList(backlogs=backlogs_list)
                
                self.error_count = 0
                self.error_messages = []

                # Update the state with the validated backlogs
                state['deliverable'] = self.current_task.description
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
        for backlog in state['deliverable_backlog_map'][self.current_task.description]:
            while(True):
                response = self.detailed_requirements.invoke({"backlog":backlog, "deliverable":state['deliverable'], "context":self.current_task.additional_info, "feedback":self.error_messages})
                try:
                    # parsed_response = json.loads(response)
                    if "question" in response.keys():
                        self.current_task.task_status = Status.AWAITING.value
                        self.current_task.question = response['question']
                        return {**state}
                    elif "description" in response.keys():
                        self.backlog_requirements[backlog] = response
                        self.error_count = 0
                        self.error_messages = []
                        break
                except Exception as e:
                    print(f"Error parsing response for backlog: {backlog}, {e}")
                    self.error_count += 1
                    error_message = f"Error in generated detailed requirements format: {str(e)}"
                    print(error_message)
                    self.error_messages.append(error_message)
                    
                    if self.error_count >= self.max_retries:
                        print("Max retries reached. Halting")
                        self.error_count = 0
                        return {**state}
        self.current_task.task_status = Status.INPROGRESS.value
        return {**state}

    def generate_response(self, state: PlannerState):
        if self.current_task.task_status == Status.INPROGRESS.value:
            response = Task(description="All Backlogs for the deliverable is successfully generated proceed further", task_status=Status.INPROGRESS.value, additional_info='',question='')
        elif self.current_task.task_status == Status.AWAITING.value:
            response = self.current_task
        else:
            response = Task(description=self.current_task.description, task_status=Status.ABANDONED.value, additional_info=self.current_task.additional_info, question=self.current_task.question)

        if state['response'] is None:
            state["response"] = response
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
