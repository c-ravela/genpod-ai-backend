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
from models.models import PlannedIssue, PlannedTask
from models.planner_models import BacklogList, Segregation
from tools.file_system import FS
from utils.logger import logger


class PlannerWorkFlow(BaseWorkFlow[PlannerPrompts]):
    """
    A workflow class to manage the planning process for tasks and issues.

    This class directs the flow of planning by routing to specific nodes based on the current planner state,
    invoking language model prompts, and updating the state accordingly.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        llm: LLM,
        use_rag: bool = False
    ):
        """
        Initialize the PlannerWorkFlow.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Name of the agent.
            llm (LLM): Language model instance used for generating prompts.
            use_rag (bool): Flag to determine if Retrieval-Augmented Generation is enabled.
        """
        super().__init__(agent_id, agent_name, PlannerPrompts(use_rag), llm, use_rag)
        self.file_count = 0

    @route_on_errors
    def router(self, state: PlannerState) -> str:
        """
        Determine the next workflow node based on the current planner state.

        This method inspects the planner's operational_mode and current_mode_stage to decide which node should execute next.
        The decision logic is:
          - For TASK_PLANNING mode:
              • If current_mode_stage is DELIVERABLE_BREAKDOWN, route to the TASK_DELIVERABLE_BREAKDOWN node.
              • If current_mode_stage is REQUIREMENTS_ANALYSIS, route to the REQUIREMENTS_ANALYSIS node.
              • If current_mode_stage is TASK_WORKPACKAGE_UPDATE, route to the TASK_WORKPACKAGE_UPDATE node.
              • If current_mode_stage is FINISHED (using IssuePlanningStage for fallback), route to the EXIT node.
          - For ISSUE_PLANNING mode:
              • If current_mode_stage is ISSUE_BREAKDOWN, route to the ISSUE_BREAKDOWN node.
              • If current_mode_stage is ISSUE_WORKPACKAGE_UPDATE, route to the ISSUE_WORKPACKAGE_UPDATE node.
              • If current_mode_stage is FINISHED, route to the EXIT node.
          - For any unknown or unmatched stage, a warning is logged and the workflow defaults to the EXIT node.

        Args:
            state (PlannerState): The current planner state, including operational_mode and current_mode_stage.

        Returns:
            str: The identifier of the next node to execute in the workflow.
        """
        func_name = "router"
        logger.debug(f"[{func_name}] Routing invoked with operational_mode: {state.operational_mode} and current_mode_stage: {state.current_mode_stage}")      
            
        if state.operational_mode == PlannerMode.TASK_PLANNING:
            logger.debug(f"{func_name}: Detected TASK_PLANNING mode.")
            if state.current_mode_stage == TaskPlanningStage.DELIVERABLE_BREAKDOWN:
                logger.debug(f"{func_name}: Stage is DELIVERABLE_BREAKDOWN; routing to TASK_DELIVERABLE_BREAKDOWN node.")
                return str(PlannerNodeEnum.TASK_DELIVERABLE_BREAKDOWN)
            elif state.current_mode_stage == TaskPlanningStage.REQUIREMENTS_ANALYSIS:
                logger.debug(f"{func_name}: Stage is REQUIREMENTS_ANALYSIS; routing to REQUIREMENTS_ANALYSIS node.")
                return str(PlannerNodeEnum.REQUIREMENTS_ANALYSIS)
            elif state.current_mode_stage == TaskPlanningStage.TASK_WORKPACKAGE_UPDATE:
                logger.debug(f"{func_name}: Stage is TASK_WORKPACKAGE_UPDATE; routing to TASK_WORKPACKAGE_UPDATE node.")
                return str(PlannerNodeEnum.TASK_WORKPACKAGE_UPDATE)
            elif state.current_mode_stage == IssuePlanningStage.FINISHED:
                logger.debug(f"{func_name}: Stage is FINISHED; routing to EXIT node.")
                return str(PlannerNodeEnum.EXIT)
            else:
                logger.warning(f"{func_name}: Unrecognized Task Planning stage: {state.current_mode_stage}. Defaulting to EXIT node.")
        elif state.operational_mode == PlannerMode.ISSUE_PLANNING:
            logger.debug(f"{func_name}: Detected ISSUE_PLANNING mode.")
            if state.current_mode_stage == IssuePlanningStage.ISSUE_BREAKDOWN:
                logger.debug(f"{func_name}: Stage is ISSUE_BREAKDOWN; routing to ISSUE_BREAKDOWN node.")
                return str(PlannerNodeEnum.ISSUE_BREAKDOWN)
            elif state.current_mode_stage == IssuePlanningStage.ISSUE_WORKPACKAGE_UPDATE:
                logger.debug(f"{func_name}: Stage is ISSUE_WORKPACKAGE_UPDATE; routing to ISSUE_WORKPACKAGE_UPDATE node.")
                return str(PlannerNodeEnum.ISSUE_WORKPACKAGE_UPDATE)
            elif state.current_mode_stage == IssuePlanningStage.FINISHED:
                logger.debug(f"{func_name}: Stage is FINISHED; routing to EXIT node.")
                return str(PlannerNodeEnum.EXIT)
            else:
                logger.warning(f"{func_name}: Unrecognized Issue Planning stage: {state.current_mode_stage}. Defaulting to EXIT node.")
        else:
            logger.warning(f"{func_name}: Unknown operational mode: {state.operational_mode}. Defaulting to EXIT node.")
        
        logger.debug(f"{func_name}: No matching stage found; defaulting to EXIT node.")
        return str(PlannerNodeEnum.EXIT)

    @record_node(PlannerNodeEnum.ENTRY)
    def entry_node(self, state: PlannerState) -> PlannerState:
        """
        Initialize the planning process by setting the appropriate operational mode and stage.

        This entry node examines the current project and task/issue statuses to determine whether to start task planning
        or issue planning. It verifies if the current task or issue has been processed before by checking processed_item_ids,
        and then sets the operational mode and stage accordingly:
          - For a project in PLANNING status:
              • If the current task is NEW and unprocessed, clear existing planned tasks, set mode to TASK_PLANNING,
                set stage to DELIVERABLE_BREAKDOWN, and add the task ID to processed_item_ids.
              • If the task has been processed before, set the stage to TASK_WORKPACKAGE_UPDATE.
          - For a project in RESOLVING status:
              • If the current issue is NEW and unprocessed, clear existing planned issues, set mode to ISSUE_PLANNING,
                set stage to ISSUE_BREAKDOWN, and add the issue ID to processed_item_ids.
              • If the issue has been processed before, set the stage to ISSUE_WORKPACKAGE_UPDATE.
          - For any other project status, set the operational mode to FINISHED.

        Args:
            state (PlannerState): The current state including project status, task/issue status, and processed item IDs.

        Returns:
            PlannerState: The updated planner state with operational mode and stage initialized.
        """
        func_name = "entry_node"
        logger.debug(f"{func_name}: Entering with project_status: {state.project_status} and task_status: {state.current_task.task_status}")

        if state.project_status == PStatus.PLANNING:
            logger.debug(f"[{func_name}] Project status is {PStatus.PLANNING}.")
            if state.current_task.task_status == Status.NEW:
                if state.current_task.task_id in state.processed_item_ids:
                    logger.info(f"[{func_name}] Task with ID {state.current_task.task_id} has been processed previously. Marking for update.")
                    state.operational_mode = PlannerMode.TASK_PLANNING
                    state.current_mode_stage = TaskPlanningStage.TASK_WORKPACKAGE_UPDATE
                else:
                    logger.debug(f"[{func_name}] Current task is NEW and unprocessed. Preparing for task planning.")
                    state.planned_tasks.clear()
                    state.operational_mode = PlannerMode.TASK_PLANNING
                    state.current_mode_stage = TaskPlanningStage.DELIVERABLE_BREAKDOWN
                    state.processed_item_ids.add(state.current_task.task_id)
                    logger.info(f"[{func_name}] Operational mode set to {PlannerMode.TASK_PLANNING} with stage {TaskPlanningStage.DELIVERABLE_BREAKDOWN}. Added task ID {state.current_task.task_id} to processed_item_ids and cleared planned tasks queue.")
            else:
                state.operational_mode = PlannerMode.FINISHED
                logger.warning(f"[{func_name}] Unexpected task status '{state.current_task.task_status}' for a project in {PStatus.EXECUTING} status. No mode change performed.")
        elif state.project_status == PStatus.RESOLVING:
            logger.debug(f"[{func_name}] Project status is {PStatus.RESOLVING}.")
            if state.current_issue.issue_status == Status.NEW:
                if state.current_issue.issue_id in state.processed_item_ids:
                    logger.info(f"[{func_name}] Issue with ID {state.current_issue.issue_id} has been processed previously. Marking for update.")
                    state.operational_mode = PlannerMode.ISSUE_PLANNING
                    state.current_mode_stage = IssuePlanningStage.ISSUE_WORKPACKAGE_UPDATE
                else:
                    logger.debug(f"[{func_name}] Current issue is NEW and unprocessed. Preparing for issue planning.")
                    state.planned_issues.clear()
                    state.operational_mode = PlannerMode.ISSUE_PLANNING
                    state.current_mode_stage = IssuePlanningStage.ISSUE_BREAKDOWN
                    state.processed_item_ids.add(state.current_issue.issue_id)
                    logger.info(f"[{func_name}] Operational mode set to {PlannerMode.ISSUE_PLANNING} with stage {IssuePlanningStage.ISSUE_BREAKDOWN}. Added issue ID {state.current_issue.issue_id} to processed_item_ids and cleared planned issues queue.")
            else:
                state.operational_mode = PlannerMode.FINISHED
                logger.warning(f"[{func_name}] Unexpected issue status '{state.current_issue.issue_status}' for a project in {PStatus.RESOLVING} status. No mode change performed.")
        else:
            state.operational_mode = PlannerMode.FINISHED
            logger.warning(f"[{func_name}] Unexpected project status '{state.project_status}'. Operational mode set to {PlannerMode.FINISHED}; no changes made to the stage.")

        logger.debug(f"[{func_name}] Exiting with operational_mode: {state.operational_mode} and current_mode_stage: {state.current_mode_stage}")
        return state

    @record_node(PlannerNodeEnum.TASK_DELIVERABLE_BREAKDOWN)
    @handle_errors_and_reset
    def task_breakdown_node(self, state: PlannerState) -> PlannerState:
        """
        Execute the deliverable breakdown stage to generate backlog items for each task deliverable.

        This node processes each deliverable in the state's deliverable_list by:
          1. Sending a task breakdown prompt to the language model with the deliverable description, the markdown-formatted
             requirements document, additional context, and any previous error feedback.
          2. Expecting a JSON-formatted response representing a list of backlog items.
          3. Parsing the response and wrapping it in a BacklogList.
          4. Appending an entry to the state's planned_backlogs with the deliverable ID, description, and generated backlogs.

        After all deliverables are processed, the node updates the stage to REQUIREMENTS_ANALYSIS.

        Args:
            state (PlannerState): The current state containing the deliverable queue, requirements document, and context.

        Returns:
            PlannerState: The updated state with planned_backlogs populated and stage set to REQUIREMENTS_ANALYSIS.
        """
        func_name = "task_breakdown_node"
        logger.debug(f"[{func_name}] Entering: Starting to process deliverable queue.")

        while state.deliverable_list.has_pending_items():
            deliverable = state.deliverable_list.get_next_item()
            logger.debug(f"[{func_name}] Processing deliverable with task_id: {deliverable.task_id} and description: {deliverable.description}")

            llm_output = self.invoke(
                self.prompts.task_breakdown_prompt,
                {
                    'deliverable': deliverable.description,
                    'context': f"{state.requirements_document.to_markdown()}\n\n{state.additional_information}",
                    'feedback': state.error_message
                },
                'string'
            )
            logger.debug(f"[{func_name}] LLM response for deliverable {deliverable.task_id}: {llm_output.response}")

            backlogs_list = ast.literal_eval(llm_output.response)
            logger.debug(f"[{func_name}] Parsed backlog items for deliverable {deliverable.task_id}: {backlogs_list}")

            state.planned_backlogs.append({
                'deliverable_id': deliverable.task_id,
                'deliverable_description': deliverable.description,
                'backlogs': BacklogList(backlogs_list)
            })
            logger.info(f"[{func_name}] Added planned backlog for deliverable {deliverable.task_id}.")

        state.current_mode_stage = TaskPlanningStage.REQUIREMENTS_ANALYSIS
        logger.debug(f"[{func_name}] Updated current_mode_stage to {TaskPlanningStage.REQUIREMENTS_ANALYSIS}.")

        logger.debug(f"[{func_name}] Exiting with updated state.")
        return state

    @record_node(PlannerNodeEnum.REQUIREMENTS_ANALYSIS)
    @handle_errors_and_reset
    def requirements_analyzer_node(self, state: PlannerState) -> PlannerState:
        """
        Analyze detailed requirements for each backlog item and generate planned tasks.

        This node iterates over each entry in planned_backlogs. For every backlog item within each deliverable:
          1. It invokes a detailed requirements prompt with the backlog item, deliverable description, markdown-formatted
             requirements, additional context, and any error feedback.
          2. The JSON response is cleaned, parsed, and merged with the deliverable details.
          3. It determines if function creation is required by invoking the _task_segregation method.
          4. Constructs a new PlannedTask with the parent_task_id set to the deliverable ID.
          5. Appends the new PlannedTask to the state's planned_tasks and writes the corresponding work package file.
          6. Finally, it marks the processed deliverable as DONE in the deliverable_list.

        After processing, the node updates the stage to FINISHED.

        Args:
            state (PlannerState): The current state with planned_backlogs, requirements, additional context, and deliverable_list.

        Returns:
            PlannerState: The updated state with new PlannedTasks, work package files stored, and deliverables marked as DONE.
        """
        func_name = "requirements_analyzer_node"
        logger.debug(f"{func_name}: Beginning detailed requirements analysis for {len(state.planned_backlogs)} backlog entries.")

        for backlog_info in state.planned_backlogs:
            deliverable_id = backlog_info.get("deliverable_id")
            deliverable_description = backlog_info.get("deliverable_description", "")
            backlog_list = backlog_info.get("backlogs")  # Expected to be an instance of BacklogList

            logger.debug(f"[{func_name}] Processing deliverable '{deliverable_id}' with description: {deliverable_description}")

            for backlog in backlog_list:
                logger.debug(f"[{func_name}] Processing backlog item for deliverable '{deliverable_id}': {backlog}")

                llm_output = self.invoke(
                    self.prompts.detailed_requirements_prompt,
                    {
                        "backlog": backlog,
                        "deliverable": deliverable_description,
                        "context": f"{state.requirements_document.to_markdown()}\n\n{state.additional_information}",
                        "feedback": state.error_message or ""
                    },
                    "string"
                )
                logger.debug(f"[{func_name}] Received LLM response for backlog '{backlog}': {llm_output.response}")

                cleaned_response = self._clean_json_response(llm_output.response)
                logger.debug(f"[{func_name}] Cleaned response for backlog '{backlog}': {cleaned_response}")

                parsed_response: dict = json.loads(cleaned_response)
                logger.debug(f"[{func_name}] Parsed response for backlog '{backlog}': {parsed_response}")

                is_function_generation_required = self._task_segregation(backlog, parsed_response)
                logger.debug(f"[{func_name}] Function generation required for backlog '{backlog}': {is_function_generation_required}")

                planned_task = PlannedTask(
                    parent_task_id=deliverable_id,
                    task_status=Status.NEW,
                    is_function_generation_required=is_function_generation_required
                )
                logger.debug(f"[{func_name}] Created PlannedTask with task ID: {planned_task.task_id} for deliverable '{deliverable_id}'")

                task_details = {
                    "parent_task_id": deliverable_id,
                    "task_id": planned_task.task_id,
                    "work_package_name": backlog,
                    "deliverable_description": deliverable_description,
                    **parsed_response
                }
                planned_task.description = json.dumps(task_details)
                logger.debug(f"[{func_name}] Set PlannedTask description for backlog '{backlog}': {planned_task.description}")

                state.planned_tasks.add_item(planned_task)
                logger.info(f"[{func_name}] Added PlannedTask for deliverable '{deliverable_id}' with task ID: {planned_task.task_id}")

                self._write_workpackage_file(state, planned_task, package_type="task")

            for deliverable in state.deliverable_list.items:
                if deliverable.task_id == deliverable_id:
                    deliverable.task_status = Status.DONE
                    logger.info(f"[{func_name}] Marked deliverable {deliverable.task_id} as DONE.")

        state.current_mode_stage = TaskPlanningStage.FINISHED
        logger.debug(f"[{func_name}] Set current_mode_stage to {TaskPlanningStage.FINISHED}.")

        logger.debug(f"[{func_name}] Exiting with updated state.")
        return state

    @record_node(PlannerNodeEnum.TASK_WORKPACKAGE_UPDATE)
    @handle_errors_and_reset
    def task_workpackage_update_node(self, state: PlannerState) -> PlannerState:
        """
        Update task work packages based on human-provided feedback.

        This node processes update instructions extracted from human feedback to modify existing task work packages.
        The process includes:
          1. Extracting update instructions from human feedback via the LLM.
          2. Identifying target PlannedTask objects in the state's planned_tasks based on the provided target_id.
          3. For each matching PlannedTask, invoking an update prompt with current task details and update changes,
             then updating the task description with the returned JSON response.
          4. Updating the corresponding work package file on disk.
          5. Marking associated deliverables in deliverable_list as DONE after updates.

        Args:
            state (PlannerState): The current state containing human feedback, planned_tasks, and project directory.

        Returns:
            PlannerState: The updated state with revised PlannedTask descriptions, updated files, and deliverable statuses set to DONE.
        """
        func_name = "task_workpackage_update_node"
        logger.debug(f"[{func_name}] Entering update process with human feedback: {state.human_feedback}")
    
        # Step 1: Extract update instructions.
        extraction_response = self.invoke(
            self.prompts.workpackage_update_extraction_prompt,
            {"feedback": state.human_feedback},
            "json"
        )
        update_instructions = ast.literal_eval(extraction_response.response)
        logger.debug(f"[{func_name}] Extracted update instructions: {update_instructions}")

        # Step 2: Process each update instruction.
        for instruction in update_instructions:
            target_id = instruction.get("target_id")
            update_changes = instruction.get("update_changes")
            if not target_id or not update_changes:
                logger.warning(f"[{func_name}] Incomplete update instruction: {instruction}")
                continue

            logger.debug(f"[{func_name}] Processing update for target_id: {target_id} with changes: {update_changes}")

            # Identify tasks to update.
            tasks_to_update = [task for task in state.planned_tasks.items 
                            if task.parent_task_id == target_id or task.task_id == target_id]
            if not tasks_to_update:
                logger.warning(f"[{func_name}] No PlannedTask found for target_id: {target_id}")
                continue

            # Step 3: Update each targeted PlannedTask.
            for task in tasks_to_update:
                logger.debug(f"[{func_name}] Updating PlannedTask with task_id: {task.task_id}")
                update_prompt_input = {
                    "current_work_package": task.description,
                    "update_changes": update_changes
                }
                update_response = self.invoke(
                    self.prompts.workpackage_update_prompt,
                    update_prompt_input,
                    "json"
                )
                logger.debug(f"[{func_name}] Received update response for task {task.task_id}: {update_response.response}")

                updated_details = update_response.response
                logger.debug(f"[{func_name}] Updated details for task {task.task_id}: {updated_details}")

                task.description = json.dumps(updated_details)
                logger.info(f"[{func_name}] Updated PlannedTask {task.task_id} description.")

                # Step 4: Update the file on disk in place using the helper.
                self._update_workpackage_file(task, state, package_type="task", details=updated_details)
                logger.info(f"[{func_name}] Updated file on disk for task {task.task_id}.")

        updated_deliverable_ids = set()
        for instruction in update_instructions:
            target_id = instruction.get("target_id")
            if not target_id:
                continue
            # First, check if target_id matches a deliverable in the deliverable_list.
            deliverable_found = False
            for deliverable in state.deliverable_list.items:
                if deliverable.task_id == target_id:
                    updated_deliverable_ids.add(deliverable.task_id)
                    deliverable_found = True
                    break
            # If not, assume target_id is a PlannedTask id; find its parent_task_id.
            if not deliverable_found:
                for task in state.planned_tasks.items:
                    if task.task_id == target_id:
                        updated_deliverable_ids.add(task.parent_task_id)
                        break

        for d_id in updated_deliverable_ids:
            for deliverable in state.deliverable_list.items:
                if deliverable.task_id == d_id:
                    deliverable.task_status = Status.DONE
                    logger.info(f"[{func_name}] Marked deliverable {d_id} as DONE due to update instruction.")

        state.current_mode_stage = TaskPlanningStage.FINISHED
        logger.debug(f"[{func_name}] Update process completed. Current mode stage set to {TaskPlanningStage.FINISHED}.")
        return state

    @record_node(PlannerNodeEnum.ISSUE_BREAKDOWN)
    @handle_errors_and_reset
    def issues_preparation_node(self, state: PlannerState) -> PlannerState:
        """
        Process the issue breakdown stage to generate planned issues.

        This node iterates over each issue in the state's issue_list by:
          1. Reading the file content of the issue.
          2. Invoking the issues segregation prompt via the LLM with issue details, file content, and additional context.
          3. Validating and parsing the LLM response using the Segregation model.
          4. Creating a new PlannedIssue using the original issue data combined with the validated response.
          5. Adding the new PlannedIssue to the planned_issues queue.
          6. Writing the issue work package file to disk.
          7. Marking each processed issue as DONE.
          8. Updating the stage to FINISHED.

        Args:
            state (PlannerState): The current state containing issue_list, requirements, additional context, and project directory.

        Returns:
            PlannerState: The updated state with new PlannedIssue entries, issues marked as DONE, and stage set to FINISHED.
        """
        func_name = "issues_preparation_node"
        logger.debug(f"[{func_name}] Entering. Processing {len(state.issue_list)} issues from issue_list.")

        while state.issue_list.has_pending_items():
            issue = state.issue_list.get_next_item()
            file_path = issue.file_path

            if not file_path or not os.path.isfile(file_path):
                reason = "missing" if not file_path else "not a valid file"
                issue.issue_status = Status.ABANDONED
                logger.warning(
                    f"[{func_name}] Abandoning issue {issue.issue_id}: {reason} '{file_path}'"
                )
                continue

            try:
                file_content = FS.read_file(file_path)
            except Exception as e:
                issue.issue_status = Status.ABANDONED
                logger.error(
                    f"[{func_name}] Abandoning issue {issue.issue_id} due to read error: {e}"
                )
                continue

            logger.debug(f"[{func_name}] Read file content from: {file_path}")

            llm_output = self.invoke_with_pydantic_model(
                self.prompts.issues_segregation_prompt,
                {
                    "issue_details": issue.issue_details(),
                    "file_content": file_content,
                    "context": state.additional_information
                },
                Segregation
            )
            logger.debug(f"[{func_name}] Received LLM output for issue_id {issue.issue_id}: {llm_output.response}")

            validated_response = llm_output.response
            logger.debug(f"[{func_name}] Validated LLM response for issue_id {issue.issue_id}: {validated_response}")

            planned_issue = PlannedIssue(
                parent_id=issue.issue_id,
                status=Status.NEW,
                file_path=issue.file_path,
                line_number=issue.line_number,
                description=issue.description,
                suggestions=issue.suggestions,
                is_function_generation_required=validated_response.requires_function_creation
            )
            logger.info(f"[{func_name}] Created PlannedIssue for issue_id {issue.issue_id} with status {planned_issue.status}")

            state.planned_issues.add_item(planned_issue)
            logger.info(f"[{func_name}] Added PlannedIssue for issue_id {issue.issue_id} to planned issues.")

            self._write_workpackage_file(state, planned_issue, package_type="issue")
            logger.debug(f"[{func_name}] Work package file written for issue {issue.issue_id}.")
            issue.issue_status = Status.DONE

        state.current_mode_stage = IssuePlanningStage.FINISHED
        logger.debug(f"[{func_name}] Set current_mode_stage to {IssuePlanningStage.FINISHED}. Exiting node.")
        return state

    @record_node(PlannerNodeEnum.ISSUE_WORKPACKAGE_UPDATE)
    @handle_errors_and_reset
    def issue_workpackage_update_node(self, state: PlannerState) -> PlannerState:
        """
        Update issue work packages based on human-provided feedback.

        This node processes update instructions extracted from human feedback to modify existing issue work packages.
        The procedure includes:
          1. Extracting update instructions via the LLM from the human feedback.
          2. Identifying target PlannedIssue objects based on the provided target_id.
          3. For each matching PlannedIssue, invoking an update prompt to merge new update changes into the current details.
          4. Updating the PlannedIssue description with the merged details.
          5. Updating the corresponding work package file on disk.
          6. Marking associated issues in issue_list as DONE.

        Args:
            state (PlannerState): The current state including human feedback, planned_issues, and project directory.

        Returns:
            PlannerState: The updated state with revised PlannedIssue descriptions, updated files, and issues marked as DONE.
        """
        func_name = "issue_workpackage_update_node"
        logger.debug(f"[{func_name}] Entering. Processing human feedback: {state.human_feedback}")
        
        extraction_response = self.invoke(
            self.prompts.workpackage_update_extraction_prompt,
            {"feedback": state.human_feedback},
            "json"
        )
        update_instructions = ast.literal_eval(extraction_response.response)
        logger.debug(f"[{func_name}] Extracted update instructions: {update_instructions}")
  
        # Step 2: Process each update instruction.
        for instruction in update_instructions:
            target_id = instruction.get("target_id")
            update_changes = instruction.get("update_changes")
            if not target_id or not update_changes:
                logger.warning(f"[{func_name}] Incomplete update instruction: {instruction}")
                continue

            logger.debug(f"[{func_name}] Processing update for target_id: {target_id} with changes: {update_changes}")

            # Identify issues to update.
            issues_to_update = [issue for issue in state.planned_issues.items 
                                if issue.parent_id == target_id or issue.id == target_id]
            if not issues_to_update:
                logger.warning(f"[{func_name}] No PlannedIssue found for target_id: {target_id}")
                continue

            # Step 3: Update each targeted PlannedIssue.
            for issue in issues_to_update:
                logger.debug(f"[{func_name}] Updating PlannedIssue with issue_id: {issue.id}")
                update_prompt_input = {
                    "current_work_package": issue.model_dump_json(),
                    "update_changes": update_changes
                }
                update_response = self.invoke(
                    self.prompts.workpackage_update_prompt,
                    update_prompt_input,
                    "json"
                )
                logger.debug(f"[{func_name}] LLM update response for issue {issue.id}: {update_response.response}")

                updated_details = update_response.response
                for i, existing_issue in enumerate(state.planned_issues.items):
                    if existing_issue.id == issue.id:
                        state.planned_issues.items[i] = issue.model_copy(update=updated_details)
                        issue = issue.model_copy(update=updated_details)
                        break
                logger.info(f"[{func_name}] Updated PlannedIssue {issue.id}.")

                # Step 4: Update the file on disk in place using the helper.
                self._update_workpackage_file(issue, state, package_type="issue", details=json.loads(issue.model_dump_json()))
                logger.info(f"[{func_name}] Successfully updated work package file for issue {issue.id}.")

        updated_issue_ids = set()
        for instruction in update_instructions:
            target_id = instruction.get("target_id")
            if not target_id:
                continue
            # Check if target_id matches an issue in issue_list.
            for issue in state.issue_list.items:
                if issue.issue_id == target_id:
                    updated_issue_ids.add(issue.issue_id)
                    break
            # Otherwise, if target_id is a PlannedIssue id, find its parent_id.
            else:
                for planned_issue in state.planned_issues.items:
                    if planned_issue.id == target_id:
                        updated_issue_ids.add(planned_issue.parent_id)
                        break

        for u_id in updated_issue_ids:
            for issue in state.issue_list.items:
                if issue.issue_id == u_id:
                    issue.issue_status = Status.DONE
                    logger.info(f"[{func_name}] Marked issue {u_id} as DONE based on update instructions.")

        state.current_mode_stage = IssuePlanningStage.FINISHED
        logger.debug(f"[{func_name}] Exiting after processing update instructions.")
        return state

    @record_node(PlannerNodeEnum.EXIT)
    def exit_node(self, state: PlannerState) -> PlannerOutput:
        """
        Finalize the planning process and adjust the status of the current task or issue.

        Depending on the operational mode and current stage, this node sets:
          - For TASK_PLANNING mode:
              • Current task status to DONE if stage is FINISHED, or ABANDONED otherwise.
          - For ISSUE_PLANNING mode:
              • Current issue status to DONE if stage is FINISHED, or ABANDONED otherwise.
          - Logs a warning for any unknown operational mode.

        Args:
            state (PlannerState): The current state containing operational mode and stage.

        Returns:
            PlannerOutput: The final planner state with updated task or issue status.
        """
        func_name = "exit_node"
        logger.debug(f"[{func_name}] Entering with operational_mode: {state.operational_mode} and current_mode_stage: {state.current_mode_stage}")

        if state.operational_mode == PlannerMode.TASK_PLANNING:
            logger.debug(f"[{func_name}] Operational mode: {PlannerMode.TASK_PLANNING}")
            if state.current_mode_stage == TaskPlanningStage.FINISHED:
                state.current_task.task_status = Status.DONE
                logger.info(f"[{func_name}] Task planning finished; setting current task status to {Status.DONE}.")
            else:
                state.current_task.task_status = Status.ABANDONED
                logger.info(f"[{func_name}] Task planning not finished; setting current task status to {Status.ABANDONED}.")
        elif state.operational_mode == PlannerMode.ISSUE_PLANNING:
            logger.debug(f"[{func_name}] Operational mode: {PlannerMode.ISSUE_PLANNING}")
            if state.current_mode_stage == IssuePlanningStage.FINISHED:
                state.current_issue.issue_status = Status.DONE
                logger.info(f"[{func_name}] Issue planning finished; setting current issue status to {Status.DONE}.")
            else:
                state.current_issue.issue_status = Status.ABANDONED
                logger.info(f"[{func_name}] Issue planning not finished; setting current issue status to {Status.ABANDONED}.")
        else:
            logger.warning(f"[{func_name}] Unknown operational mode encountered: {state.operational_mode}")

        logger.debug(f"[{func_name}] Exiting with updated state: {state}")
        return state

    def _clean_json_response(self, response: str) -> str:
        """
        Remove markdown code block markers from a JSON response string.

        This method strips extraneous formatting (e.g., ```json markers) from the LLM response to ensure valid JSON.

        Args:
            response (str): The raw JSON response string.

        Returns:
            str: The cleaned JSON string.
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
        Determine whether the work package requires function creation based on its requirements.

        Args:
            workpackage_name (str): The name of the work package.
            requirements (dict): The detailed requirements for the work package.

        Returns:
            bool: True if function creation is required, False otherwise.
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

    def _write_workpackage_file(self, state: PlannerState, planned_item, package_type: str) -> None:
        """
        Writes a work package file for a planned item (task or issue) and updates the workpackage_file_map.

        The workpackage_file_map in PlannerState is structured as:
            {
                parent_id: {
                    planned_item_id: file_path,
                    ...
                },
                ...
            }
        This method determines the correct directory based on the package_type, creates (or overwrites) a file named
        "<planned_item_id>.json" in that directory, writes the JSON representation of the planned item's description
        to the file, and updates the mapping accordingly.

        Args:
            state (PlannerState): The current planner state, which includes project_directory and workpackage_file_map.
            planned_item: The planned item object (either a PlannedTask or PlannedIssue). For tasks, it must have attributes:
                        task_id, parent_task_id, description; for issues, it must have attributes:
                        issue_id, parent_id, description.
            package_type (str): Either "task" or "issue", indicating the type of work package.
        """

        func_name = "_write_workpackage_file"
        base_folder = "work_packages" if package_type == "task" else "issue_packages"
        base_dir = os.path.join(state.project_directory, "docs", base_folder)
        os.makedirs(base_dir, exist_ok=True)
    
        try:
            if package_type == "task":
                item_id = planned_item.task_id
                content_to_write = json.loads(planned_item.description)
            elif package_type == "issue":
                item_id = planned_item.id
                content_to_write = json.loads(planned_item.model_dump_json())
            else:
                raise ValueError(f"Unsupported package_type '{package_type}'")

            file_path = os.path.join(base_dir, f"{item_id}.json")

            with codecs.open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content_to_write, f, indent=4)
            logger.info(f"[{func_name}] Work package for {item_id} written to file: {file_path} using utf-8 encoding.")
        except UnicodeEncodeError:
            try:
                with codecs.open(file_path, 'w', encoding='utf-8-sig') as f:
                    json.dump(planned_item.description, f, indent=4)
                logger.info(f"[{func_name}] Work package for {item_id} written to file: {file_path} using utf-8-sig encoding.")
            except Exception as e:
                logger.error(f"[{func_name}] Failed to write work package for {item_id} at file {file_path} with utf-8-sig: {e}")
                return
        except Exception as e:
            logger.error(f"[{func_name}] Failed to write work package for {item_id} at file {file_path}: {e}")
            return

    def _update_workpackage_file(self, planned_item, state: PlannerState, package_type: str, details: dict) -> None:
        """
        Updates the work package file for a planned item (task or issue) in place.

        The file path is computed based on the project's directory, the appropriate folder (either "docs/work_packages" 
        for tasks or "docs/issue_packages" for issues), and the planned item’s ID (task_id or issue_id). The file is named 
        "<planned_item_id>.json" and is overwritten with the new details.

        Args:
            planned_item: The planned item object (PlannedTask or PlannedIssue) with attributes:
                        - For tasks: task_id, description.
                        - For issues: issue_id, description.
            state (PlannerState): The current planner state, including project_directory.
            package_type (str): Either "task" or "issue".
            details (dict): The updated work package details.
        """
        func_name = "_update_workpackage_file"
        base_folder = "work_packages" if package_type == "task" else "issue_packages"
        base_dir = os.path.join(state.project_directory, "docs", base_folder)
        os.makedirs(base_dir, exist_ok=True)
        
        # Compute item ID and file path.
        item_id = planned_item.task_id if package_type == "task" else planned_item.id
        file_path = os.path.join(base_dir, f"{item_id}.json")

        logger.debug(f"[{func_name}] Updating file for planned_item_id '{item_id}' at path: {file_path}")
        try:
            with codecs.open(file_path, 'w', encoding='utf-8') as f:
                json.dump(details, f, indent=4)
            logger.info(f"[{func_name}] Successfully updated work package for '{item_id}' at file: {file_path} using utf-8 encoding.")
        except UnicodeEncodeError:
            try:
                with codecs.open(file_path, 'w', encoding='utf-8-sig') as f:
                    json.dump(details, f, indent=4)
                logger.info(f"[{func_name}] Successfully updated work package for '{item_id}' at file: {file_path} using utf-8-sig encoding.")
            except Exception as e:
                logger.error(f"[{func_name}] Failed to update work package for '{item_id}' at file {file_path} with utf-8-sig: {e}")
        except Exception as e:
            logger.error(f"[{func_name}] Failed to update work package for '{item_id}' at file {file_path}: {e}")
