import ast
import codecs
import json
import os

from agents.planner._internal.planner_mode_enum import (IssuePlanningStage,
                                                        PlannerMode,
                                                        TaskPlanningStage)
from agents.planner._internal.planner_node_enum import PlannerNodeEnum
from agents.planner._internal.planner_prompt import PlannerPrompts
from agents.planner._internal.planner_state import PlannerOutput, PlannerState
from core.decorators import (handle_errors_and_reset, record_node,
                             route_on_errors)
from core.workflow import BaseWorkFlow
from llms.llm import LLM
from models.constants import PStatus, Status
from models.models import PlannedIssue, PlannedTask, PlannedTaskQueue
from models.planner_models import BacklogList, Segregation
from tools.file_system import FS
from utils.logs.logging_utils import logger


class PlannerWorkFlow(BaseWorkFlow[PlannerPrompts]):

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        llm: LLM,
        use_rag = False
    ):
        super().__init__(agent_id, agent_name, PlannerPrompts(use_rag), llm, use_rag)
        self.file_count = 0

    @route_on_errors
    def router(self, state: PlannerState) -> str:
        """
        Routes the planner workflow to the appropriate node based on the current state.

        The router inspects the operational mode and current mode stage within the PlannerState,
        and determines the next node in the workflow. The routing logic is as follows:

        For TASK_PLANNING:
        - If the current mode stage is TASK_BREAKDOWN, route to the TASK_BREAKDOWN node.
        - If the current mode stage is REQUIREMENTS_ANALYZER, route to the REQUIREMENTS_ANALYZER node.
        - If the current mode stage is FINISHED (using IssuePlanningStage.FINISHED in this branch), route to the EXIT node.

        For ISSUE_PLANNING:
        - If the current mode stage is ISSUE_BREAKDOWN, route to the ISSUE_BREAKDOWN node.
        - If the current mode stage is FINISHED, route to the EXIT node.

        If an unexpected operational mode or mode stage is encountered, a warning is logged and
        the router defaults to the EXIT node.

        Args:
            state (PlannerState): The current state of the planner, which includes the operational mode
                                    and the current mode stage.

        Returns:
            str: The string representation of the next node in the planner workflow.
        """
        logger.debug("Routing invoked with operational_mode: %s and current_mode_stage: %s",
                    state.operational_mode, state.current_mode_stage)
                    
        if state.operational_mode == PlannerMode.TASK_PLANNING:
            logger.debug("Operational mode set to TASK_PLANNING")
            if state.current_mode_stage == TaskPlanningStage.TASK_BREAKDOWN:
                logger.debug("Current stage is TASK_BREAKDOWN; routing to TASK_BREAKDOWN node")
                return str(PlannerNodeEnum.TASK_BREAKDOWN)
            elif state.current_mode_stage == TaskPlanningStage.REQUIREMENTS_ANALYZER:
                logger.debug("Current stage is REQUIREMENTS_ANALYZER; routing to REQUIREMENTS_ANALYZER node")
                return str(PlannerNodeEnum.REQUIREMENTS_ANALYZER)
            elif state.current_mode_stage == IssuePlanningStage.FINISHED:
                logger.debug("Current stage is FINISHED (from IssuePlanningStage); routing to EXIT node")
                return str(PlannerNodeEnum.EXIT)
            else:
                logger.warning("Unexpected Task Planning stage encountered: %s. Defaulting to EXIT node.",
                            state.current_mode_stage)
        elif state.operational_mode == PlannerMode.ISSUE_PLANNING:
            logger.debug("Operational mode set to ISSUE_PLANNING")
            if state.current_mode_stage == IssuePlanningStage.ISSUE_BREAKDOWN:
                logger.debug("Current stage is ISSUE_BREAKDOWN; routing to ISSUE_BREAKDOWN node")
                return str(PlannerNodeEnum.ISSUE_BREAKDOWN)
            elif state.current_mode_stage == IssuePlanningStage.FINISHED:
                logger.debug("Current stage is FINISHED; routing to EXIT node")
                return str(PlannerNodeEnum.EXIT)
            else:
                logger.warning("Unexpected Issue Planning stage encountered: %s. Defaulting to EXIT node.",
                            state.current_mode_stage)

        logger.debug("No matching stage found; routing to EXIT node by default")
        return str(PlannerNodeEnum.EXIT)

    @record_node(PlannerNodeEnum.ENTRY)
    def entry_node(self, state: PlannerState) -> PlannerState:
        """
        Entry node for the Planner Workflow.

        This method initializes the planner's operational mode and current mode stage based on the
        project's status and the current task's status. Specifically:

        - For a project in the EXECUTING status:
            - If the current task is NEW, the planner switches to TASK_PLANNING mode and sets the stage to TASK_BREAKDOWN.
            - Otherwise, a warning is logged indicating an unexpected task status.
        
        - For a project in the RESOLVING status:
            - If the current task is NEW, the planner switches to ISSUE_PLANNING mode and sets the stage to ISSUE_BREAKDOWN.
            - Otherwise, a warning is logged indicating an unexpected task status.
        
        - For any other project status, a warning is logged.

        Args:
            state (PlannerState): The current state of the planner, including project and task statuses.

        Returns:
            PlannerState: The updated planner state with the operational mode and mode stage set accordingly.
        """
        logger.debug("Entering entry_node with project_status: %s and task_status: %s",
                    state.project_status, state.current_task.task_status)

        if state.project_status == PStatus.EXECUTING:
            logger.debug("Project status is EXECUTING.")
            if state.current_task.task_status == Status.NEW:
                logger.debug("Current task status is NEW. Preparing for task planning: Clearing planned tasks, setting operational mode to TASK_PLANNING, and stage to TASK_BREAKDOWN.")
                state.planned_tasks.clear()
                state.operational_mode = PlannerMode.TASK_PLANNING
                state.current_mode_stage = TaskPlanningStage.TASK_BREAKDOWN
                logger.info("Operational mode updated to TASK_PLANNING with stage TASK_BREAKDOWN. Planned tasks queue cleared.")
            else:
                logger.warning("Unexpected current task status '%s' for a project in EXECUTING status. No operational mode change performed.",
                            state.current_task.task_status)
        elif state.project_status == PStatus.RESOLVING:
            logger.debug("Project status is RESOLVING.")
            if state.current_issue.issue_status == Status.NEW:
                logger.debug("Current issue status is NEW. Preparing for issue planning: Clearing planned issues, setting operational mode to ISSUE_PLANNING, and stage to ISSUE_BREAKDOWN.")
                state.planned_issues.clear()
                state.operational_mode = PlannerMode.ISSUE_PLANNING
                state.current_mode_stage = IssuePlanningStage.ISSUE_BREAKDOWN
                logger.info("Operational mode updated to ISSUE_PLANNING with stage ISSUE_BREAKDOWN. Planned issues queue cleared.")
            else:
                logger.warning("Unexpected current issue status '%s' for a project in RESOLVING status. No operational mode change performed.",
                            state.current_issue.issue_status)
        else:
            state.operational_mode = PlannerMode.FINISHED
            logger.warning("Unexpected project status '%s'. Operational mode set to FINISHED; no changes made to mode stage.",
                        state.project_status)

        logger.debug("Exiting entry_node with operational_mode: %s and current_mode_stage: %s",
                    state.operational_mode, state.current_mode_stage)
        return state

    @record_node(PlannerNodeEnum.TASK_BREAKDOWN)
    @handle_errors_and_reset
    def task_breakdown_node(self, state: PlannerState) -> PlannerState:
        """
        Process the task breakdown stage of the planning workflow.

        In this node, the planner invokes a language model (LLM) using the task breakdown prompt,
        passing in the current task description, requirements document (formatted as Markdown), any
        additional information, and feedback from previous errors. The LLM's response is expected to
        be a string representation of a list of backlog items. This response is parsed and used to update
        the state's planned backlogs. After processing the LLM response, the state is advanced to the
        REQUIREMENTS_ANALYZER stage.

        Args:
            state (PlannerState): The current state of the planner, which includes details about the current task,
                                    requirements, and any error messages.

        Returns:
            PlannerState: The updated planner state with the planned backlogs and the current mode stage set to
                        REQUIREMENTS_ANALYZER.
        """
        logger.debug("Entering task_breakdown_node with task description: %s", state.current_task.description)
    
        llm_response = self.invoke(
            self.prompts.task_breakdown_prompt,
            {
                "deliverable": state.current_task.description,
                "context": f"{state.requirements_document.to_markdown()}\n\n{state.additional_information}",
                "feedback": state.error_message
            }, 'string'
        )
        logger.debug("Received LLM response: %s", llm_response.response)

        backlogs_list = ast.literal_eval(llm_response.response)
        logger.debug("Parsed LLM response into backlogs_list: %s", backlogs_list)

        state.planned_backlogs = BacklogList(backlogs=backlogs_list).backlogs
        logger.info("Updated planned_backlogs in state.")

        state.current_mode_stage = TaskPlanningStage.REQUIREMENTS_ANALYZER
        logger.debug("Updated current_mode_stage to: %s", state.current_mode_stage)

        logger.debug("Exiting task_breakdown_node with updated state.")
        return state

    @record_node(PlannerNodeEnum.REQUIREMENTS_ANALYZER)
    @handle_errors_and_reset
    def requirements_analyzer_node(self, state: PlannerState) -> PlannerState:
        """
        Analyze detailed requirements for each backlog item and update the planner state with planned tasks.

        For each backlog item in the state's planned backlogs, this node:
        1. Invokes the detailed requirements prompt via the language model (LLM) to gather additional
            information on the task.
        2. Cleans and parses the LLM's JSON response.
        3. Determines if function generation is required for the given backlog using the _task_segregation method.
        4. Creates a new PlannedTask using the parsed details and augments its description with the parsed
            response along with task identifiers.
        5. Adds the newly created PlannedTask to the state's planned tasks queue.

        After processing all backlog items, the method:
        - Writes the planned tasks (work packages) to files.
        - Updates the state's file count with the total number of files written.
        - Transitions the state's current mode stage to FINISHED.

        Args:
            state (PlannerState): The current planner state containing the planned backlogs, task details, and other relevant information.

        Returns:
            PlannerState: The updated planner state including the newly added planned tasks and file count.
        """
        logger.debug("Entering requirements_analyzer_node with %d planned backlog item(s).", len(state.planned_backlogs))
      
        for backlog in state.planned_backlogs:
            logger.debug("Processing backlog item: '%s'", backlog)
            
            llm_response = self.invoke(
                self.prompts.detailed_requirements_prompt,
                {
                    'backlog': backlog,
                    'deliverable': state.current_task.description,
                    'context': f"{state.requirements_document.to_markdown()}\n\n{state.additional_information}",
                    'feedback': state.error_message
                },
                'string'
            )
            logger.debug("Received LLM response for backlog '%s': %s", backlog, llm_response.response)
        

            cleaned_response = self._clean_json_response(llm_response.response)
            logger.debug("Cleaned LLM response for backlog '%s': %s", backlog, cleaned_response)
        
            parsed_response: dict = json.loads(cleaned_response)
            logger.debug("Parsed response for backlog '%s': %s", backlog, parsed_response)

            is_function_generation_required = self._task_segregation(backlog, parsed_response)
            logger.debug("Function generation required for backlog '%s': %s", backlog, is_function_generation_required)

            planned_task = PlannedTask(
                parent_task_id=state.current_task.task_id,
                task_status=Status.NEW,
                is_function_generation_required=is_function_generation_required
            )
            logger.debug("Created PlannedTask with task ID: %s", planned_task.task_id)
        
            task_details = {
                "task_id": planned_task.task_id,
                "work_package_name": backlog,
                **parsed_response
            }
            planned_task.description = json.dumps(task_details)
            logger.debug("Updated PlannedTask description for backlog '%s': %s", backlog, planned_task.description)
        
            state.planned_tasks.add_item(planned_task)
            logger.info("Added PlannedTask for backlog '%s' with task ID: %s", backlog, planned_task.task_id)

        files_written, total_files_written = self._write_workpackages_to_files(state.project_directory, state.planned_tasks)
        state.file_count = total_files_written
        logger.info("Work packages written to files. Files written: %d, Total files: %d", files_written, total_files_written)

        state.current_mode_stage = TaskPlanningStage.FINISHED
        logger.debug("Transitioned current_mode_stage to FINISHED")
        
        logger.debug("Exiting requirements_analyzer_node")
        return state

    @record_node(PlannerNodeEnum.ISSUE_BREAKDOWN)
    @handle_errors_and_reset
    def issues_preparation_node(self, state: PlannerState) -> PlannerState:
        """
        Prepare issues by segregating issue details and generating planned issues.

        This node processes the current issue by:
        1. Reading the file content from the current issue's file path.
        2. Invoking the language model (LLM) using the issues segregation prompt with the issue details
            and file content. The LLM response is validated against the Segregation model.
        3. Creating a new PlannedIssue using the current issue's data combined with the LLM's validated response.
        4. Adding the newly created PlannedIssue to the state's collection of planned issues.

        Args:
            state (PlannerState): The current state of the planner, which includes the current issue.

        Returns:
            PlannerState: The updated state with the new planned issue added.
        """
        logger.debug("Entering issues_preparation_node for issue_id: %s", state.current_issue.issue_id)

        file_content = FS.read_file(state.current_issue.file_path)
        logger.debug("Read file content from %s", state.current_issue.file_path)
        
        llm_output = self.invoke_with_pydantic_model(
            self.prompts.issues_segregation_prompt,
            {
                "issue_details": state.current_issue.issue_details(),
                "file_content": file_content
            },
            Segregation
        )
        logger.debug("LLM output received for issue_id %s: %s", state.current_issue.issue_id, llm_output.response)
    
        validated_response = llm_output.response
        logger.debug("Validated response: %s", validated_response)
    
        planned_issue = PlannedIssue(
            parent_id=state.current_issue.issue_id,
            status=Status.NEW,
            file_path=state.current_issue.file_path,
            line_number=state.current_issue.line_number,
            description=state.current_issue.description,
            suggestions=state.current_issue.suggestions,
            is_function_generation_required=validated_response.requires_function_creation
        )
        logger.info("Created PlannedIssue for issue_id %s with status %s", state.current_issue.issue_id, planned_issue.status)
    
        state.planned_issues.add_item(planned_issue)
        logger.info("Added PlannedIssue with parent_id %s to planned issues", planned_issue.parent_id)
        
        state.current_mode_stage = IssuePlanningStage.FINISHED
        logger.debug("Exiting issues_preparation_node")
        return state

    @record_node(PlannerNodeEnum.EXIT)
    def exit_node(self, state: PlannerState) -> PlannerOutput:
        """
        Finalize the planning process and update the status of the current task or issue.

        Depending on the operational mode and the current mode stage, this node sets the status of:
        - The current task (in TASK_PLANNING mode):
            - To INPROGRESS if the TaskPlanningStage is FINISHED.
            - To ABANDONED if the TaskPlanningStage is not FINISHED.
        - The current issue (in ISSUE_PLANNING mode):
            - To INPROGRESS if the IssuePlanningStage is FINISHED.
            - To ABANDONED if the IssuePlanningStage is not FINISHED.

        If an unknown operational mode is encountered, a warning is logged.

        Args:
            state (PlannerState): The current state of the planner, including operational mode and current mode stage.

        Returns:
            PlannerOutput: The updated state with the task or issue status adjusted accordingly.
        """
        logger.debug("Entering exit_node with operational_mode: %s and current_mode_stage: %s",
                    state.operational_mode, state.current_mode_stage)

        if state.operational_mode == PlannerMode.TASK_PLANNING:
            logger.debug("Operational mode: TASK_PLANNING")
            if state.current_mode_stage == TaskPlanningStage.FINISHED:
                state.current_task.task_status = Status.INPROGRESS
                logger.info("Task planning finished; setting current task status to INPROGRESS.")
            else:
                state.current_task.task_status = Status.ABANDONED
                logger.info("Task planning not finished; setting current task status to ABANDONED.")
        elif state.operational_mode == PlannerMode.ISSUE_PLANNING:
            logger.debug("Operational mode: ISSUE_PLANNING")
            if state.current_mode_stage == IssuePlanningStage.FINISHED:
                state.current_issue.issue_status = Status.INPROGRESS
                logger.info("Issue planning finished; setting current issue status to INPROGRESS.")
            else:
                state.current_issue.issue_status = Status.ABANDONED
                logger.info("Issue planning not finished; setting current issue status to ABANDONED.")
        else:
            logger.warning("Unknown operational mode encountered: %s", state.operational_mode)

        logger.debug("Exiting exit_node with updated state: %s", state)
        return state

    def _clean_json_response(self, response: str) -> str:
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

    def _task_segregation(self, workpackage_name: str, requirements: dict) -> bool:
        """
        Determines if a work package requires function creation.

        Args:
            workpackage_name (str): Name of the work package.
            requirements (dict): Detailed requirements for the work package.

        Returns:
            bool: True if function creation is required, otherwise False.
        """
        logger.info(f"{self.agent_name}: Initiating task segregation for work package: {workpackage_name}")

        max_retries = 3
        while(True):
            try:
                llm_output = self.invoke_with_pydantic_model(
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

                if self.error_count >= max_retries:
                    logger.error(f"{self.agent_name}: Max retries reached for work package '{workpackage_name}'.")
                    self.error_count = 0
                    return False

    def _write_workpackages_to_files(
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
