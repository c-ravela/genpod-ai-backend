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
from utils.logger import logger


class PlannerWorkFlow(BaseWorkFlow[PlannerPrompts]):

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        llm: LLM,
        use_rag: bool = False
    ):
        super().__init__(agent_id, agent_name, PlannerPrompts(use_rag), llm, use_rag)
        self.file_count = 0


    @route_on_errors
    def router(self, state: PlannerState) -> str:
        """
        Determines the next node in the planning workflow based on the current state.

        The router examines the PlannerState's operational_mode and current_mode_stage to decide which node to execute next.
        The routing logic is as follows:
        - For TASK_PLANNING:
            • If current_mode_stage equals TaskPlanningStage.DELIVERABLE_BREAKDOWN, route to the TASK_DELIVERABLE_BREAKDOWN node.
            • If current_mode_stage equals TaskPlanningStage.REQUIREMENTS_ANALYZER, route to the REQUIREMENTS_ANALYZER node.
            • If current_mode_stage equals TaskPlanningStage.TASK_WORKPACKAGE_UPDATE, route to the TASK_WORKPACKAGE_UPDATE node.
            • If current_mode_stage equals IssuePlanningStage.FINISHED, route to the EXIT node.
        - For ISSUE_PLANNING:
            • If current_mode_stage equals IssuePlanningStage.ISSUE_BREAKDOWN, route to the ISSUE_BREAKDOWN node.
            • If current_mode_stage equals IssuePlanningStage.ISSUE_WORKPACKAGE_UPDATE, route to the ISSUE_WORKPACKAGE_UPDATE node.
            • If current_mode_stage equals IssuePlanningStage.FINISHED, route to the EXIT node.
        - If no matching stage is found or an unexpected mode is detected, a warning is logged and the router defaults to the EXIT node.

        Args:
            state (PlannerState): The current state of the planner, including operational_mode and current_mode_stage.

        Returns:
            str: The identifier of the next node in the workflow.
        """
        func_name = "router"
        logger.debug(f"[{func_name}] Routing invoked with operational_mode: {state.operational_mode} and current_mode_stage: {state.current_mode_stage}")
            
        if state.operational_mode == PlannerMode.TASK_PLANNING:
            logger.debug(f"[{func_name}] Detected operational mode: {PlannerMode.TASK_PLANNING}")
            if state.current_mode_stage == TaskPlanningStage.DELIVERABLE_BREAKDOWN:
                logger.debug(f"[{func_name}] Stage is {TaskPlanningStage.DELIVERABLE_BREAKDOWN}; routing to {PlannerNodeEnum.TASK_DELIVERABLE_BREAKDOWN}")
                return str(PlannerNodeEnum.TASK_DELIVERABLE_BREAKDOWN)
            elif state.current_mode_stage == TaskPlanningStage.REQUIREMENTS_ANALYSIS:
                logger.debug(f"[{func_name}] Stage is {TaskPlanningStage.REQUIREMENTS_ANALYSIS}; routing to {PlannerNodeEnum.REQUIREMENTS_ANALYSIS}")
                return str(PlannerNodeEnum.REQUIREMENTS_ANALYSIS)
            elif state.current_mode_stage == TaskPlanningStage.TASK_WORKPACKAGE_UPDATE:
                logger.debug(f"[{func_name}] Stage is {TaskPlanningStage.TASK_WORKPACKAGE_UPDATE}; routing to {PlannerNodeEnum.TASK_WORKPACKAGE_UPDATE}")
                return str(PlannerNodeEnum.TASK_WORKPACKAGE_UPDATE)
            elif state.current_mode_stage == IssuePlanningStage.FINISHED:
                logger.debug(f"[{func_name}] Stage is {IssuePlanningStage.FINISHED}; routing to {PlannerNodeEnum.EXIT}")
                return str(PlannerNodeEnum.EXIT)
            else:
                logger.warning(f"[{func_name}] Unexpected Task Planning stage: {state.current_mode_stage}. Defaulting to {PlannerNodeEnum.EXIT}")
        elif state.operational_mode == PlannerMode.ISSUE_PLANNING:
            logger.debug(f"[{func_name}] Detected operational mode: {PlannerMode.ISSUE_PLANNING}")
            if state.current_mode_stage == IssuePlanningStage.ISSUE_BREAKDOWN:
                logger.debug(f"[{func_name}] Stage is {IssuePlanningStage.ISSUE_BREAKDOWN}; routing to {PlannerNodeEnum.ISSUE_BREAKDOWN}")
                return str(PlannerNodeEnum.ISSUE_BREAKDOWN)
            elif state.current_mode_stage == IssuePlanningStage.ISSUE_WORKPACKAGE_UPDATE:
                logger.debug(f"[{func_name}] Stage is {IssuePlanningStage.ISSUE_WORKPACKAGE_UPDATE}; routing to {PlannerNodeEnum.ISSUE_WORKPACKAGE_UPDATE}")
                return str(PlannerNodeEnum.ISSUE_WORKPACKAGE_UPDATE)
            elif state.current_mode_stage == IssuePlanningStage.FINISHED:
                logger.debug(f"[{func_name}] Stage is {IssuePlanningStage.FINISHED}; routing to {PlannerNodeEnum.EXIT}")
                return str(PlannerNodeEnum.EXIT)
            else:
                logger.warning(f"[{func_name}] Unexpected Issue Planning stage: {state.current_mode_stage}. Defaulting to {PlannerNodeEnum.EXIT}")
        else:
            logger.warning(f"[{func_name}] Unknown operational mode: {state.operational_mode}. Defaulting to {PlannerNodeEnum.EXIT}")
        
        logger.debug(f"[{func_name}] No matching stage found; routing to {PlannerNodeEnum.EXIT} by default.")
        return str(PlannerNodeEnum.EXIT)

    @record_node(PlannerNodeEnum.ENTRY)
    def entry_node(self, state: PlannerState) -> PlannerState:
        """
        Entry node for the Planner Workflow.

        This method initializes the planner's operational mode and current stage based on the project's status
        and the current task/issue status. It checks whether the current task or issue has been processed before
        by looking up its ID in the processed_item_ids set. The behavior is as follows:
        
        - For a project in the EXECUTING status:
            - If the current task is NEW and its task_id is not in processed_item_ids, the planner clears any
            existing planned tasks, sets the operational mode to PlannerMode.TASK_PLANNING, advances the stage to 
            TaskPlanningStage.DELIVERABLE_BREAKDOWN, and then adds the task_id to processed_item_ids.
            - If the current task's task_id is already in processed_item_ids, the planner marks it for update by
            setting the stage to TaskPlanningStage.TASK_WORKPACKAGE_UPDATE.
        
        - For a project in the RESOLVING status:
            - If the current issue is NEW and its issue_id is not in processed_item_ids, the planner clears any
            existing planned issues, sets the operational mode to PlannerMode.ISSUE_PLANNING, advances the stage to 
            IssuePlanningStage.ISSUE_BREAKDOWN, and then adds the issue_id to processed_item_ids.
            - If the current issue's issue_id is already in processed_item_ids, the planner marks it for update by
            setting the stage to IssuePlanningStage.ISSUE_WORKPACKAGE_UPDATE.
        
        - For any other project status, the operational mode is set to PlannerMode.FINISHED.

        Args:
            state (PlannerState): The current state of the planner, including project status, current task/issue status,
                                and processed_item_ids.

        Returns:
            PlannerState: The updated state with the operational mode and current stage set appropriately.
        """
        func_name = "entry_node"
        logger.debug(f"[{func_name}] Entering with project_status: {state.project_status} and task_status: {state.current_task.task_status}")

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
        Process the deliverable breakdown stage of the planning workflow.

        This node iterates over the deliverables queued in state.deliverable_list.
        For each deliverable, the node performs the following steps:
        - Invokes the task breakdown prompt via the LLM using:
                • The deliverable's description.
                • The requirements document (formatted as Markdown).
                • Additional contextual information.
                • Any previous error feedback.
        - Expects the LLM to return a JSON-formatted string representing a list of backlog items.
        - Parses the response into a list of backlog items and wraps it into a BacklogList instance.
        - Appends a dictionary to state.planned_backlogs containing:
                • 'deliverable_id': the deliverable's existing task_id.
                • 'deliverable_description': the deliverable's description.
                • 'backlogs': the generated BacklogList.
        
        After processing all deliverables, the node advances the current mode stage to 
        TaskPlanningStage.REQUIREMENTS_ANALYSIS, indicating that detailed requirements analysis is next.

        Args:
            state (PlannerState): The current state of the planner, which includes:
                - A queue of deliverables (state.deliverable_list).
                - The requirements document.
                - Additional contextual information.
                - Any error feedback.

        Returns:
            PlannerState: The updated state with the planned_backlogs list populated and the current mode stage set to REQUIREMENTS_ANALYSIS.
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
                'backlogs': BacklogList(backlogs=backlogs_list)
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
        Analyze detailed requirements for each backlog item and update the planner state with planned tasks.

        This node iterates over the list of planned backlogs stored in state.planned_backlogs. Each entry in planned_backlogs 
        is a dictionary containing:
        - deliverable_id: The unique ID of the deliverable (parent).
        - deliverable_description: The description of the deliverable.
        - backlogs: A BacklogList instance holding the list of backlog items for that deliverable.
        
        For each backlog item within each deliverable, the node performs the following:
        1. Invokes the detailed requirements prompt via the LLM with:
                - The backlog item.
                - The deliverable's description.
                - The requirements document (formatted as Markdown).
                - Additional contextual information.
                - Any error feedback.
        2. Cleans and parses the LLM's JSON response.
        3. Determines whether function generation is required via the _task_segregation method.
        4. Creates a new PlannedTask with its parent_task_id set to the deliverable's ID.
            The task details are built by merging the parsed response with the deliverable's description.
        5. Adds the newly created PlannedTask to the state's planned_tasks queue.
        6. Writes the new work package to disk by invoking _write_workpackage_file. This helper writes the file as
            "<planned_task_id>.json" in the appropriate folder and updates state.workpackage_file_map so that:
                - The outer key is the deliverable_id.
                - The inner dictionary maps the planned task's ID to its file path.
        
        After processing all backlog items, the node advances the current mode stage to TaskPlanningStage.FINISHED.

        Args:
            state (PlannerState): The current state of the planner containing:
                - planned_backlogs: a list of dictionaries with keys 'deliverable_id', 'deliverable_description', 
                and 'backlogs' (a BacklogList instance).
                - requirements_document, additional_information, and error_message.

        Returns:
            PlannerState: The updated state with new PlannedTasks added to planned_tasks and work package files stored,
                        and the current mode stage set to FINISHED.
        """
        func_name = "requirements_analyzer_node"
        logger.debug(f"[{func_name}] Entering with {len(state.planned_backlogs)} planned backlog entries.")

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

        state.current_mode_stage = TaskPlanningStage.FINISHED
        logger.debug(f"[{func_name}] Set current_mode_stage to {TaskPlanningStage.FINISHED}.")

        logger.debug(f"[{func_name}] Exiting with updated state.")
        return state

    @record_node(PlannerNodeEnum.TASK_WORKPACKAGE_UPDATE)
    @handle_errors_and_reset
    def task_workpackage_update_node(self, state: PlannerState) -> PlannerState:
        """
        Update task work packages based on human feedback.

        This node processes human feedback (from state.human_feedback) to determine which task work packages
        need updating and what changes to apply. It performs the following steps:
        
        1. Extract update instructions by invoking the workpackage_update_extraction_prompt with human feedback.
            The LLM returns a JSON list of instructions, each containing:
                - "target_id": either a deliverable (parent) ID or a specific work package (task) ID.
                - "update_changes": a string describing the changes to be applied.
                
        2. For each instruction, identify target PlannedTask objects in state.planned_tasks.items by matching if
            the target_id equals either the task's parent_task_id or the task's task_id.
        
        3. For each targeted PlannedTask:
                - Invoke the workpackage_update_prompt with the current task details (task.description) and update_changes.
                - Parse and merge the returned JSON details with the current task details.
                - Update the PlannedTask's description with the merged details.
        
        4. For each updated PlannedTask, update its work package file on disk in place by calling _update_workpackage_file.
            The file path is computed as "<task_id>.json" in the "docs/work_packages" folder.
        
        Args:
            state (PlannerState): The current planner state including human_feedback, planned_tasks, and project_directory.
        
        Returns:
            PlannerState: The updated state with revised PlannedTask descriptions and updated work package files.
        """
        func_name = "task_workpackage_update_node"
        logger.debug(f"[{func_name}] Entering. Processing human feedback: {state.human_feedback}")
    
        # Step 1: Extract update instructions.
        extraction_response = self.invoke(
            self.prompts.workpackage_update_extraction_prompt,
            {"feedback": state.human_feedback},
            "string"
        )
        update_instructions = json.loads(extraction_response.response)
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
                    "string"
                )
                logger.debug(f"[{func_name}] LLM update response for task {task.task_id}: {update_response.response}")

                updated_details = json.loads(self._clean_json_response(update_response.response))
                current_details = json.loads(task.description)

                merged_details = {**current_details, **updated_details}
                task.description = json.dumps(merged_details)
                logger.info(f"[{func_name}] Updated PlannedTask {task.task_id} description.")

                # Step 4: Update the file on disk in place using the helper.
                self._update_workpackage_file(task, state, package_type="task", details=merged_details)

        state.current_mode_stage = TaskPlanningStage.FINISHED
        logger.debug(f"[{func_name}] Update process completed. Current mode stage set to {TaskPlanningStage.FINISHED}.")
        return state

    @record_node(PlannerNodeEnum.ISSUE_BREAKDOWN)
    @handle_errors_and_reset
    def issues_preparation_node(self, state: PlannerState) -> PlannerState:
        """
        Process the issue breakdown stage for issue planning.

        This node iterates over all issues provided in state.issue_list. For each issue, it performs the following steps:
        1. Reads the file content from the issue's file_path.
        2. Invokes the issues segregation prompt via the LLM with the issue's details, file content, and additional context.
        3. Validates and parses the LLM's response using the Segregation model.
        4. Creates a new PlannedIssue by combining the issue's data with the validated LLM response. 
            The new PlannedIssue uses the issue's own issue_id as its parent_id.
        5. Adds the new PlannedIssue to the state's planned_issues queue.
        6. Writes the issue work package to disk by calling _write_workpackage_file (which computes the file path based on the issue_id).
        7. After processing all issues, advances the current mode stage to IssuePlanningStage.FINISHED.

        Args:
            state (PlannerState): The current planner state, which includes:
                - issue_list: A list of Issue objects to be processed.
                - requirements_document, additional_information, and error_message.
                - project_directory for file storage.

        Returns:
            PlannerState: The updated state with new PlannedIssue objects added to planned_issues and the current mode stage set to FINISHED.
        """
        func_name = "issues_preparation_node"
        logger.debug(f"[{func_name}] Entering. Processing {len(state.issue_list)} issues from issue_list.")

        while state.issue_list.has_pending_items():
            issue = state.issue_list.get_next_item()
            logger.debug(f"[{func_name}] Processing issue with issue_id: {issue.issue_id} and description: {issue.description}")

            file_content = FS.read_file(issue.file_path)
            logger.debug(f"[{func_name}] Read file content from: {issue.file_path}")

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

        state.current_mode_stage = IssuePlanningStage.FINISHED
        logger.debug(f"[{func_name}] Set current_mode_stage to {IssuePlanningStage.FINISHED}. Exiting node.")
        return state

    @record_node(PlannerNodeEnum.ISSUE_WORKPACKAGE_UPDATE)
    @handle_errors_and_reset
    def issue_workpackage_update_node(self, state: PlannerState) -> PlannerState:
        """
        Update issue work packages based on human feedback.

        This node processes human feedback (from state.human_feedback) to determine which issue work packages need
        updating and what changes to apply. It follows these steps:
        
        1. Extract update instructions by invoking the workpackage_update_extraction_prompt with human feedback.
            The LLM returns a JSON list of instructions, each containing:
                - "target_id": either a deliverable (parent) ID or a specific work package (issue) ID.
                - "update_changes": a string describing the changes to be applied.
                
        2. For each instruction, identify target PlannedIssue objects in state.planned_issues.items by matching if
            the target_id equals either the issue's parent_id or the issue's issue_id.
        
        3. For each targeted PlannedIssue:
                - Invoke the workpackage_update_prompt with the current issue details (issue.description) and update_changes.
                - Parse and merge the returned JSON details with the current issue details.
                - Update the PlannedIssue's description with the merged details.
        
        4. For each updated PlannedIssue, update its work package file on disk in place by calling _update_workpackage_file.
            The file path is computed as "<issue_id>.json" in the "docs/issue_packages" folder.
        
        Args:
            state (PlannerState): The current planner state including human_feedback, planned_issues, and project_directory.
        
        Returns:
            PlannerState: The updated state with revised PlannedIssue descriptions and updated work package files.
        """
        func_name = "issue_workpackage_update_node"
        logger.debug(f"[{func_name}] Entering. Processing human feedback: {state.human_feedback}")
        
        extraction_response = self.invoke(
            self.prompts.workpackage_update_extraction_prompt,
            {"feedback": state.human_feedback},
            "string"
        )
        update_instructions = json.loads(extraction_response.response)
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
                    "current_work_package": issue.description,
                    "update_changes": update_changes
                }
                update_response = self.invoke(
                    self.prompts.workpackage_update_prompt,
                    update_prompt_input,
                    "string"
                )
                logger.debug(f"[{func_name}] LLM update response for issue {issue.id}: {update_response.response}")

                updated_details = json.loads(self._clean_json_response(update_response.response))
                current_details = json.loads(issue.description)
                merged_details = {**current_details, **updated_details}
                issue.description = json.dumps(merged_details)
                logger.info(f"[{func_name}] Updated PlannedIssue {issue.id} description.")

                # Step 4: Update the file on disk in place using the helper.
                self._update_workpackage_file(issue.id, merged_details, state, package_type="issue")

        state.current_mode_stage = IssuePlanningStage.FINISHED
        logger.debug(f"[{func_name}] Exiting after processing update instructions.")
        return state

    @record_node(PlannerNodeEnum.EXIT)
    def exit_node(self, state: PlannerState) -> PlannerOutput:
        """
        Finalize the planning process and update the status of the current task or issue.

        Depending on the operational mode and the current mode stage, this node sets the status of:
        - The current task (in TASK_PLANNING mode):
            - To DONE if the TaskPlanningStage is FINISHED.
            - To ABANDONED if the TaskPlanningStage is not FINISHED.
        - The current issue (in ISSUE_PLANNING mode):
            - To DONE if the IssuePlanningStage is FINISHED.
            - To ABANDONED if the IssuePlanningStage is not FINISHED.

        If an unknown operational mode is encountered, a warning is logged.

        Args:
            state (PlannerState): The current state of the planner, including operational mode and current mode stage.

        Returns:
            PlannerOutput: The updated state with the task or issue status adjusted accordingly.
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

        item_id = planned_item.task_id if package_type == "task" else planned_item.issue_id

        file_path = os.path.join(base_dir, f"{item_id}.json")
    
        try:
            with codecs.open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json.loads(planned_item.description), f, indent=4)
            logger.info(f"[{func_name}] Work package for {item_id} written to file: {file_path} using utf-8 encoding.")
        except UnicodeEncodeError:
            try:
                with codecs.open(file_path, 'w', encoding='utf-8-sig') as f:
                    json.dump(json.loads(planned_item.description), f, indent=4)
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
        item_id = planned_item.task_id if package_type == "task" else planned_item.issue_id
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
