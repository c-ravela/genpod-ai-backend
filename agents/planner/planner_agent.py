import ast
import codecs
import json
import os
import re
from typing import List

from pydantic import ValidationError

from agents.base.base_agent import BaseAgent
from agents.planner.planner_state import PlannerState
from llms.llm import LLM
from models.constants import PStatus, Status
from models.models import (PlannedIssue, PlannedIssuesQueue, PlannedTask,
                           PlannedTaskQueue)
from models.planner_models import BacklogList, Segregation
from prompts.planner_prompts import PlannerPrompts
from tools.file_system import FS
from utils.logs.logging_utils import logger


class PlannerAgent(BaseAgent[PlannerState, PlannerPrompts]):
    """
    PlannerAgent handles the breakdown of tasks, requirement analysis, and preparation of planned issues 
    for efficient execution.
    """
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        llm: LLM
    ) -> None:
        
        """
        Initializes the PlannerAgent with the given parameters.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Name of the agent.
            llm (LLM): Language model instance for generating responses.
        """
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

        self.error_count = 0
        self.max_retries = 3
        self.error_messages = []
        self.file_count = 0
        
        logger.info(f"{self.agent_name}: PlannerAgent initialized successfully.")

    def write_workpackages_to_files(
        self,
        output_dir: str,
        planned_tasks: PlannedTaskQueue
    ) -> tuple[int, int]:
        """
        Writes work packages from a queue to individual JSON files.

        Args:
            output_dir (str): Base directory for output files.
            planned_tasks (PlannedTaskQueue): Queue containing planned tasks.

        Returns:
            tuple[int, int]: Number of work packages written successfully and the 
            total count.
        """
        
        if len(planned_tasks) < 0:
            logger.warning(f"{self.agent_name}: No work packages available for writing.")
            return 0, self.file_count

        logger.info(f"{self.agent_name}: Writing work packages to the 'docs/work_packages' folder.")
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

                logger.info(f"{self.agent_name}: Work package written to: {file_path}")
            except UnicodeEncodeError:
                try:
                    with codecs.open(file_path, 'w', encoding='utf-8-sig') as file:
                        json.dump(work_package, file, indent=4)
                    logger.info(f"{self.agent_name}: Work package written to: {file_path} (with BOM)")
                except Exception as e:
                    logger.error(f"{self.agent_name}: Failed to write work package to {file_path}. Error: {e}")
            self.file_count += 1
            session_file_count += 1
        return session_file_count, self.file_count
    
    def new_deliverable_check(self, state: PlannerState) -> str:
        """
        Determines the next node in the workflow based on the project status and current task/issue.

        Args:
            state (PlannerState): Current state of the planner.

        Returns:
            str: Name of the next node.
        """
        self.error_messages = []
        self.file_count = BaseAgent.ensure_value(state['file_count'], 0)

        if state['project_status'] == PStatus.EXECUTING:
            if state['current_task'].task_status == Status.NEW:
                logger.info(f"{self.agent_name}: New deliverable detected. Proceeding to task breakdown.")
                return self.task_breakdown_node_name
            return self.requirements_analyzer_node_name
        elif state['project_status'] == PStatus.RESOLVING:
            if state['current_issue'].issue_status == Status.NEW:
                logger.info(f"{self.agent_name}: New issue detected. Preparing planned issues.")
                return self.issues_preparation_node_name
        
        logger.warning(f"{self.agent_name}: Invalid state detected. Unable to determine the next node.")
        return ""

    # TODO - MEDIUM: We have to segeregate the backlogs into categories
    # like Documents, Coding, Config so on. all possible options
    def task_breakdown_node(self, state: PlannerState) -> PlannerState:
        """
        Handles the breakdown of deliverables into planned tasks.

        Args:
            state (PlannerState): Current state of the planner.

        Returns:
            PlannerState: Updated state with planned tasks.
        """
        state['mode'] = 'preparing_planned_tasks'
        state['planned_tasks'] = PlannedTaskQueue()

        while True:
            try:
                logger.info(f"{self.agent_name}: Building backlogs for the deliverable: {state['current_task'].description}")
                llm_output = self.llm.invoke(self.prompts.task_breakdown_prompt, {
                    "deliverable": state['current_task'].description,
                    "context": state['context'],
                    "feedback": self.error_messages
                }, 'string')

                backlogs_list = ast.literal_eval(llm_output.response)
                
                # Validate the response using Pydantic
                state['planned_backlogs'] = BacklogList(backlogs=backlogs_list).backlogs
                logger.info(f"{self.agent_name}: Backlogs successfully generated and validated.")
                self.error_count = 0
                self.error_messages = []
                break # while loop exit
            except (ValidationError, ValueError, SyntaxError) as e:
                self.error_count += 1
                error_message = f"Error generating backlogs: {e}"
                
                logger.error(f"{self.agent_name}: {error_message}")
                self.error_messages.append(error_message)
                
                if self.error_count >= self.max_retries:
                    logger.error(f"{self.agent_name}: Max retries reached. Halting backlog generation.")
                    self.error_count = 0
                    break # while loop exit
        
        return state

    def requirements_analyzer_node(self, state: PlannerState) -> PlannerState:
        """
        Generates detailed requirements for each backlog in planned backlogs.

        Args:
            state (PlannerState): Current state of the planner.

        Returns:
            PlannerState: Updated state with detailed requirements.
        """
        state['mode'] = 'preparing_planned_tasks'
        
        for backlog in state['planned_backlogs']:
            while True:
                try:
                    logger.info(f"{self.agent_name}: Generating detailed requirements for backlog: {backlog}")

                    if state['current_task'].task_status == Status.RESPONDED:
                        context = f"{state['context']}\n{state['current_task'].additional_info}"
                    else:
                        context = state['context']

                    llm_output = self.llm.invoke(self.prompts.detailed_requirements_prompt, {
                        "backlog": backlog, 
                        "deliverable": state['current_task'].description, 
                        "context": context, 
                        "feedback": self.error_messages
                    }, 'string')

                    cleaned_response = self.clean_json_response(llm_output.response)
                    parsed_response: dict = json.loads(cleaned_response)

                    if "question" in parsed_response.keys():
                        state['current_task'].task_status = Status.AWAITING
                        state['current_task'].question = parsed_response['question']
                        logger.info(f"{self.agent_name}: Awaiting additional information for backlog: {backlog}")
                        return state
                    elif "description" in parsed_response.keys():
                        is_function_generation_required = self.task_segregation(backlog, parsed_response)
                        planned_task = PlannedTask(
                                parent_task_id=state['current_task'].task_id,
                                task_status=Status.NEW,
                                is_function_generation_required=is_function_generation_required,
                        )

                        parsed_response = {
                            "task_id": planned_task.task_id,
                            "work_package_name": backlog,
                            **parsed_response
                        }

                        planned_task.description = json.dumps(parsed_response)
                        state['planned_tasks'].add_item(planned_task)

                        logger.info(f"{self.agent_name}: Detailed requirements generated and added for backlog: {backlog}")
                        self.error_count = 0
                        self.error_messages = []
                        break # for while loop
                except Exception as e:
                    self.error_count += 1
                    error_message = f"Error in detailed requirements: {e}"
                    logger.error(f"{self.agent_name}: {error_message}")
                    self.error_messages.append(error_message)

                    if self.error_count >= self.max_retries:
                        logger.error(f"{self.agent_name}: Max retries reached for backlog: {backlog}")
                        self.error_count = 0
                        return state             

        files_written, total_files_written = self.write_workpackages_to_files(state['project_path'], state['planned_tasks'])
        state['file_count'] = total_files_written
        logger.info(f"{self.agent_name}:Wrote %d work packages. Total files written: %d", files_written, total_files_written)

        state['current_task'].task_status = Status.INPROGRESS
        return state

    def issues_preparation_node(self, state: PlannerState) -> PlannerState:
        """
        Prepares planned issues for resolving a detected issue in the project.

        Args:
            state (PlannerState): Current state of the planner.

        Returns:
            PlannerState: Updated state with planned issues.
        """
        state['mode'] = 'preparing_planned_issues'
        state['planned_issues'] = PlannedIssuesQueue()
       
        while True:
            try:
                logger.info(f"{self.agent_name}: Preparing planned issues for issue ID: {state['current_issue'].issue_id}.")
                logger.debug(f"{self.agent_name}: Issue Details: {state['current_issue']}")

                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.issues_segregation_prompt,
                    {
                        "issue_details": state['current_issue'].issue_details(),
                        "file_content": FS.read_file(state['current_issue'].file_path)
                    },
                    Segregation
                )

                validated_response = llm_output.response
                logger.info(f"{self.agent_name}: Issue ID {state['current_issue'].issue_id} segregated successfully. Details: {validated_response}")

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

                break  # while loop exit
            except FileNotFoundError as ffe:
                logger.error(f"{self.agent_name}: File not found while processing issue ID {state['current_issue'].issue_id}: {ffe}")
                self.error_count += 1
                self.error_messages.append(str(ffe))
            except Exception as e:
                logger.error(f"{self.agent_name}: Error processing issue ID {state['current_issue'].issue_id}: {e}")
                self.error_count += 1
                self.error_messages.append(str(e))

                if self.error_count >= self.max_retries:
                    logger.error(f"{self.agent_name}: Max retries reached for issue ID {state['current_issue'].issue_id}. Halting processing.")
                    self.error_count = 0
                    return state
              
        state['current_issue'].issue_status = Status.INPROGRESS
        return state

    def agent_response_node(self, state: PlannerState) -> PlannerState:
        """
        Finalizes the agent's response based on the state of planned tasks or issues.

        Args:
            state (PlannerState): Current state of the planner.

        Returns:
            PlannerState: Updated state with finalized task or issue status.
        """
        logger.info(f"{self.agent_name}: Preparing response for the current state.")

        if state['mode'] == 'preparing_planned_tasks':
            # After attempting to handle the current task with planner chains, check the task's status.
            # If the task status is:
            # - Status.INPROGRESS: The planner has successfully prepared planned tasks.
            # - Status.AWAITING: The task is waiting for some condition or input before it can proceed.
            # - Status.NEW: An error occurred during the task execution, and it was not handled properly.
            # In the case of Status.NEW, we need to abandon the task since it could not be successfully addressed by the planner.
            if state['current_task'].task_status == Status.NEW:
                state['current_task'].task_status = Status.ABANDONED
                logger.warning(f"{self.agent_name}: Task abandoned as it could not be successfully addressed.")
        elif state['mode'] == 'preparing_planned_issues':
            if state['current_issue'].issue_status == Status.NEW:
                state['current_issue'].issue_status = Status.ABANDONED
                logger.warning(f"{self.agent_name}: Issue abandoned as it could not be successfully addressed.")

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
        Determines if a work package requires function creation.

        Args:
            workpackage_name (str): Name of the work package.
            requirements (dict): Detailed requirements for the work package.

        Returns:
            bool: True if function creation is required, otherwise False.
        """
        logger.info(f"{self.agent_name}: Initiating task segregation for work package: {workpackage_name}")

        while(True):
            try:
                llm_output = self.llm.invoke_with_pydantic_model(
                    self.prompts.segregation_prompt,
                    {"work_package": f"{workpackage_name} \n {requirements}"},
                    Segregation
                )

                validated_response = llm_output.response
                logger.info(f"{self.agent_name}: Segregation result for work package '{workpackage_name}': {validated_response}")

                self.error_count = 0
                self.error_messages = []

                return validated_response.requires_function_creation
            except Exception as e:
                logger.error(f"{self.agent_name}: Error during task segregation for work package '{workpackage_name}': {e}")
                self.error_count += 1
                self.error_messages.append(str(e))

                if self.error_count >= self.max_retries:
                    logger.error(f"{self.agent_name}: Max retries reached for work package '{workpackage_name}'.")
                    self.error_count = 0
                    return False

    def clean_json_response(self, response: str) -> str:
        """
        Cleans a JSON response string by removing unnecessary code block markers.

        Args:
            response (str): JSON response string.

        Returns:
            str: Cleaned JSON string.
        """
        logger.info(f"{self.agent_name}: Cleaning JSON response.")
        cleaned_response = response.strip()

        if cleaned_response.startswith('```json') and cleaned_response.endswith('```'):
            cleaned_json = cleaned_response.removeprefix('```json').removesuffix('```').strip()
            logger.debug(f"{self.agent_name}: Removed JSON code block markers.")
        else:
            cleaned_json = cleaned_response

        return cleaned_json
