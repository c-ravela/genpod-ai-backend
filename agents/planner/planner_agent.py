import ast
import codecs
import json
import os
import re
from typing import List, Literal

from pydantic import ValidationError

from agents.agent.agent import Agent
from agents.planner.planner_state import PlannerState
from llms.llm import LLM
from models.constants import PStatus, Status
from models.models import (PlannedIssue, PlannedIssuesQueue, PlannedTask,
                           PlannedTaskQueue)
from models.planner_models import BacklogList, Segregation
from prompts.planner_prompts import PlannerPrompts
from tools.file_system import FS
from utils.logs.logging_utils import logger


class PlannerAgent(Agent[PlannerState, PlannerPrompts]):
    """
    """
    
    task_breakdown_node_name: str
    requirements_analyzer_node_name: str
    issues_preparation_node_name: str
    agent_response_node_name: str
    update_state_node_name: str

    # Mode explanation:
    # 'preparing_planned_tasks': Breaking down a general task into smaller, manageable backlog planned tasks.
    # 'preparing_planned_issues': Checking if unit test case generation is required and preparing a planned issue from the given issue.
    mode: Literal['preparing_planned_tasks', 'preparing_planned_issues']
    deliverable: str

    def __init__(self, agent_id: str, agent_name: str, llm: LLM) -> None:
        
        super().__init__(
            agent_id,
            agent_name,
            PlannerState(),
            PlannerPrompts(),
            llm
        )

        self.task_breakdown_node_name = "task_breakdown"
        self.requirements_analyzer_node_name = "requirements_analyzer"
        self.issues_preparation_node_name = "issues_preparation"
        self.agent_response_node_name = "agent_response"
        self.update_state_node_name = "update_state"

        self.mode = ''
        self.error_count = 0
        self.max_retries = 3
        self.error_messages = []
        self.file_count = 0

        self.planned_backlogs: list[str] = []

    def write_workpackages_to_files(self, output_dir: str, planned_tasks: PlannedTaskQueue) -> tuple[int, int]:
        """
        Write work packages from a dictionary to individual JSON files.

        Args:
        backlog_dict (dict): Dictionary containing work package data.
        output_dir (str): Base directory for output files.

        Returns:
        int: Number of work packages written successfully.
        """
        if len(planned_tasks) < 0:
            logger.info("----Workpackages not present----")
            return 0, self.file_count

        logger.info("----Writing workpackages to Project Docs Folder----")
        work_packages_dir = os.path.join(output_dir, "docs", "work_packages")
        os.makedirs(work_packages_dir, exist_ok=True)

        session_file_count = 0
        for planned_task in planned_tasks:
            file_name = f'work_package_{self.file_count + 1}.json'
            file_path = os.path.join(work_packages_dir, file_name)

            work_package: dict = json.loads(planned_task.description)
            
            try:
                with codecs.open(file_path, 'w', encoding='utf-8') as file:
                    json.dump(work_package, file, indent=4)

                logger.info("Workpackage written to: %s", file_path)
            except UnicodeEncodeError:
                try:
                    with codecs.open(file_path, 'w', encoding='utf-8-sig') as file:
                        json.dump(work_package, file, indent=4)

                    logger.info("Workpackage written to: %s (with BOM)", file_path)
                except Exception as e:
                    logger.error("Unable to write workpackage to filepath: %s. Error: %s", file_path, str(e))
            
            self.file_count += 1
            session_file_count += 1
        return session_file_count, self.file_count
    
    def new_deliverable_check(self, state: PlannerState) -> str:
        if state['project_status'] == PStatus.EXECUTING:
            self.mode = 'preparing_planned_tasks'

            if state['current_task'].task_status == Status.NEW:
                return self.task_breakdown_node_name
            else:
                return self.requirements_analyzer_node_name
        elif state['project_status'] == PStatus.RESOLVING:
            self.mode = 'preparing_planned_issues'
            self.deliverable = (
                f"Issue Detected:\n"
                f"-------------------------\n"
                f"{state['current_issue'].issue_details()}\n"
                f"Please review and address this issue promptly."
            )

            if state['current_issue'].issue_status == Status.NEW:
                return self.issues_preparation_node_name
            
    # TODO - MEDIUM: We have to segeregate the backlogs into categories
    # like Documents, Coding, Config so on. all possible options
    def task_breakdown_node(self, state: PlannerState) -> PlannerState:
        state['planned_tasks'] = PlannedTaskQueue()

        while(True):
            try:
                logger.info("----Working on building backlogs for the deliverable----")
                logger.info("Deliverable: %s", state['current_task'].description)

                llm_output = self.llm.invoke(self.prompts.task_breakdown_prompt, {
                        "deliverable": state['current_task'].description,
                        "context": state['context'],
                        "feedback": self.error_messages
                    },
                    'string'
                )

                backlogs_list = ast.literal_eval(llm_output.response)
                
                # Validate the response using Pydantic
                self.planned_backlogs = BacklogList(backlogs=backlogs_list).backlogs

                self.error_count = 0
                self.error_messages = []

                break # while loop exit
            except (ValidationError, ValueError, SyntaxError) as e:
                self.error_count += 1
                error_message = f"Error generating backlogs: {str(e)}"
                
                logger.error(error_message)
                self.error_messages.append(error_message)
                
                if self.error_count >= self.max_retries:
                    logger.info("Max retries reached. Halting")
                    self.error_count = 0
                    
                    break # while loop exit
        
        return state

    def requirements_analyzer_node(self, state: PlannerState) -> PlannerState:
        
        for backlog in self.planned_backlogs:
            while(True):
                try:
                    logger.info("----Now Working on Generating detailed requirements for the backlog----")
                    logger.info("Backlog: %s", backlog)

                    if state['current_task'].task_status == Status.RESPONDED:
                        context = f"{state['context']}\n{state['current_task'].additional_info}"
                    else:
                        context = state['context']

                    llm_output = self.llm.invoke(self.prompts.detailed_requirements_prompt, {
                            "backlog": backlog, 
                            "deliverable": state['current_task'].description, 
                            "context": context, 
                            "feedback": self.error_messages
                        },
                        'string'
                    )

                    # Let's clean the response to remove json prefix that llm sometimes appends to the actual text
                    # Strip whitespace from the beginning and end
                    cleaned_response = llm_output.response.strip()
                    # Check if the text starts with ```json and ends with ```
                    if cleaned_response.startswith('```json') and cleaned_response.endswith('```'):
                        # Remove the ```json prefix and ``` suffix
                        cleaned_json = cleaned_response.removeprefix('```json').removesuffix('```').strip()
                    else:
                        # If not enclosed in code blocks, use the text as is
                        cleaned_json = cleaned_response

                    parsed_response: dict = json.loads(cleaned_json)
                    logger.info("response from planner ", parsed_response)

                    if "question" in parsed_response.keys():
                        logger.info("----Awaiting for additional information on----")
                        logger.info("Question: %s", parsed_response['question'])
                        state['current_task'].task_status = Status.AWAITING
                        state['current_task'].question = parsed_response['question']
                        return state
                    elif "description" in parsed_response.keys():
                        logger.info("----Generated Detailed requirements in JSON format for the backlog----")
                        
                        is_function_generation_required = self.task_segregation(backlog, parsed_response)
                        planned_task = PlannedTask(
                                parent_task_id=state['current_task'].task_id,
                                task_status=Status.NEW,
                                is_function_generation_required=is_function_generation_required,
                        )

                        parsed_response = {
                            "task_id": f"{planned_task.task_id}",
                            "work_package_name": f"{backlog}",
                            **parsed_response
                        }

                        planned_task.description = json.dumps(parsed_response)
                        state['planned_tasks'].add_item(planned_task)

                        logger.info("Requirements in JSON: %r", parsed_response)

                        self.error_count = 0
                        self.error_messages = []

                        break # for while loop
                except Exception as e:
                    logger.info("Error parsing response for backlog: %s", backlog)
                    logger.error("%s", str(e))
                    self.error_count += 1
                    
                    error_message = f"Error in generated detailed requirements format: {str(e)}, I'm using python json.loads() to convert json to dictionary so take that into consideration."
                    logger.info("Error Message fed back to LLM: %s", error_message)
                    
                    self.error_messages.append(error_message)
                    
                    if self.error_count >= self.max_retries:
                        logger.info("Max retries reached. Halting")
                        self.error_count = 0

                        return state             
        
        state['current_task'].task_status = Status.INPROGRESS
            
        files_written, total_files_written = self.write_workpackages_to_files(state['project_path'], state['planned_tasks'])
        logger.info('Wrote down %d work packages into the project folder during the current session. Total files written during the current run %d', files_written, total_files_written)

        return state
    
    def issues_preparation_node(self, state: PlannerState) -> PlannerState:
        """
        """
        state['planned_tasks'] = PlannedIssuesQueue()
        
        while(True):
            try:
                logger.info(f"{self.agent_name}: Preparing planned issues for issue with id: {state['current_issue'].issue_id}.")
                logger.info(f"Issue: {state['current_issue']}")

                llm_output = self.llm.invoke_with_pydantic_model(self.prompts.issues_segregation_prompt, {
                        "issue_details": state['current_issue'].issue_details(),
                        "file_content": FS.read_file(state['current_issue'].file_path)
                    },
                    Segregation
                )

                validated_response = llm_output.response
                logger.info(f"Issue {state['current_issue'].issue_id} has been successfully segregated with the following details: {validated_response}")

                planned_issue = PlannedIssue(
                    parent_id=state['current_issue'].issue_id,
                    status=Status.NEW,
                    file_path=state['current_issue'].file_path,
                    line_number=state['current_issue'].line_number,
                    description=state['current_issue'].description,
                    suggestions=state['current_issue'].suggestions,
                    is_function_generation_required=validated_response.requires_function_creation
                )

                state['planned_issues'].add_item(planned_issue)
                
                self.error_count = 0
                self.error_messages = []

                break # while loop exit 
            except Exception as e:
                self.error_count += 1
                
                logger.error(e)
                self.error_messages.append(e)

                if self.error_count >= self.max_retries:
                    logger.info(f"Maximum retry attempts reached while processing issue with ID: {state['current_issue'].issue_id}.")

                    return state
            except FileNotFoundError as ffe:
                logger.error(f"{self.agent_name}: Error Occured at resolve issue: ===>{type(ffe)}<=== {ffe}.----")
                
        state['current_issue'].issue_status = Status.INPROGRESS

        return state

    def agent_response_node(self, state: PlannerState) -> PlannerState:
        if self.mode == 'preparing_planned_tasks':
            # After attempting to handle the current task with planner chains, check the task's status.
            # If the task status is:
            # - Status.INPROGRESS: The planner has successfully prepared planned tasks.
            # - Status.AWAITING: The task is waiting for some condition or input before it can proceed.
            # - Status.NEW: An error occurred during the task execution, and it was not handled properly.
            # In the case of Status.NEW, we need to abandon the task since it could not be successfully addressed by the planner.
            if state['current_task'].task_status == Status.NEW:
                state['current_task'].task_status = Status.ABANDONED
        elif self.mode == 'preparing_planned_issues':
            if state['current_issue'].issue_status == Status.NEW:
                state['current_issue'].issue_status = Status.ABANDONED

        return state
    
    def parse_backlog_tasks(self, response: str) -> List[str]:

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
    
    def task_segregation(self, workpackage_name: str, requirements: dict) -> bool:
        """
        """
        logger.info(f"---- Initiating segregation ----")
        while(True):
            try:
                llm_output = self.llm.invoke_with_pydantic_model(self.prompts.segregation_prompt, {
                        "work_package": f"{workpackage_name} \n {requirements}",
                    },
                    Segregation
                )

                validate_response = llm_output.response
                
                self.error_count = 0
                self.error_messages = []

                break # while loop exit
            except Exception as e:
                self.error_count += 1
                
                logger.error(e)
                self.error_messages.append(e)

                if self.error_count >= self.max_retries:
                    logger.info(f"Maximum retry attempts reached.")

                    return
    
        return validate_response.requires_function_creation
