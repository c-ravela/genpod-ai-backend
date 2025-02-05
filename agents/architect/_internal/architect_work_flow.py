from dataclasses import dataclass
from os import path
from typing import Any, Dict, Type

from agents.architect._internal.architect_mode_enum import *
from agents.architect._internal.architect_node_enum import ArchitectNodeEnum
from agents.architect._internal.architect_prompt import ArchitectPrompts
from agents.architect._internal.architect_state import *
from core.decorators import *
from core.workflow import BaseWorkFlow
from llms import LLM
from models.architect_models import ProjectDetails, TaskList, TaskResponse
from models.constants import PStatus, Status
from models.models import Task, TaskQueue
from tools.code import CodeFileWriter
from utils.logs.logging_utils import logger


@dataclass
class GenerationStepConfig:
    """
    Configuration for a generation step in the Architect workflow.
    
    Attributes:
        prompt (Any): The prompt object to be used for this step.
        response_model (Type): The Pydantic model class that defines the expected response.
        input_params (Dict[str, Any]): A dictionary of parameters to be passed to the prompt.
    """
    prompt: Any
    response_model: Type
    input_params: Dict[str, Any]


class ArchitectWorkFlow(BaseWorkFlow[ArchitectPrompts]):
    """
    ArchitectWorkFlow orchestrates the execution of the Architect agent's workflow.

    It maintains the internal state of the agent, processes user input, and manages the transition
    between different nodes (e.g., generating requirements, extracting tasks, etc.) by invoking
    appropriate LLM prompts.
    """

    def __init__(self, agent_id: str, agent_name: str, llm: LLM, use_rag: bool) -> None:
        """
        Initializes the ArchitectWorkFlow with the provided agent ID, name, LLM, and RAG flag.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Human-readable name for the agent.
            llm (LLM): The language model to be used by the Architect agent.
            use_rag (bool): Flag indicating whether RAG instructions should be applied in prompts.
        """
        logger.info("Initializing ArchitectWorkFlow for agent '%s' (ID: %s) with use_rag=%s", agent_name, agent_id, use_rag)
        super().__init__(agent_id, agent_name, ArchitectPrompts(use_rag), llm, use_rag)

    @route_on_errors
    def router(self, state: ArchitectState) -> str:
        """
        Determines the next node in the Architect agent's workflow based on the current state.

        This method examines the agent's operational mode and current mode stage to decide the
        appropriate next node. When the operational mode is DOCUMENT_GENERATION, the router selects
        the next node according to the current_mode_stage. If the mode or stage is unrecognized,
        it defaults to routing to the EXIT node.

        Args:
            state (ArchitectState): The current state of the architect agent.

        Returns:
            str: The identifier (as a string) of the next node to be executed.
        """
        logger.info("Router invoked for agent '%s' with state: %s", self.agent_name, state)
        
        if state.operational_mode == ArchitectAgentMode.DOCUMENT_GENERATION:
            logger.info("Operational mode is DOCUMENT_GENERATION. Current stage: %s", state.current_mode_stage)
            if state.current_mode_stage == DocumentGenerationStage.GENERATE_REQUIREMENTS:
                logger.info("Routing to GENERATE_REQUIREMENTS node.")
                return str(ArchitectNodeEnum.GENERATE_REQUIREMENTS)
            elif state.current_mode_stage == DocumentGenerationStage.EXTRACT_TASKS:
                logger.info("Routing to EXTRACT_TASKS node.")
                return str(ArchitectNodeEnum.EXTRACT_TASKS)
            elif state.current_mode_stage == DocumentGenerationStage.SAVE_REQUIREMENTS:
                logger.info("Routing to SAVE_REQUIREMENTS node.")
                return str(ArchitectNodeEnum.SAVE_REQUIREMENTS)
            elif state.current_mode_stage == DocumentGenerationStage.GATHER_PROJECT_DETAILS:
                logger.info("Routing to GATHER_PROJECT_DETAILS node.")
                return str(ArchitectNodeEnum.GATHER_PROJECT_DETAILS)
            elif state.current_mode_stage == DocumentGenerationStage.FINISHED:
                logger.info("Routing to FINISHED node.")
                return str(ArchitectNodeEnum.EXIT)
            else:
                logger.warning("Unhandled document generation stage: %s", state.current_mode_stage)
        
        logger.info("Operational mode is not recognized; routing to END node.")
        return str(ArchitectNodeEnum.EXIT)

    @record_node(ArchitectNodeEnum.ENTRY)
    def entry_node(self, state: ArchitectState) -> ArchitectState:
        """
        Entry node for processing the initial state of the architect.
        Determines the operational mode based on project and task statuses.
        
        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state after processing.
        """
        func_name = "entry_node"
        logger.debug("Agent '%s': Entering entry_node with project_status=%s and task_status=%s.",
                     self.agent_name, state.project_status, state.current_task.task_status)
       
        try:
            if state.project_status == PStatus.INITIAL:
                logger.info("Agent '%s': Function '%s': Project status is INITIAL.", self.agent_name, func_name)
                if state.current_task.task_status == Status.NEW:
                    logger.info("Agent '%s': Function '%s': Task status is NEW. Setting operational mode to DOCUMENT_GENERATION.", self.agent_name, func_name)
                    state.operational_mode = ArchitectAgentMode.DOCUMENT_GENERATION
                    state.current_mode_stage = DocumentGenerationStage.GENERATE_REQUIREMENTS
                else:
                    logger.warning("Agent '%s': Function '%s': Task status is not NEW. Setting operational mode to FINISHED.", self.agent_name, func_name)
                    state.operational_mode = ArchitectAgentMode.FINISHED
            else:
                logger.info("Agent '%s': Function '%s': Project status is not INITIAL. Setting operational mode to FINISHED.", self.agent_name, func_name)
                state.operational_mode = ArchitectAgentMode.FINISHED
            logger.debug("Agent '%s': Function '%s': Updated operational_mode: %s", self.agent_name, func_name, state.operational_mode)
        except Exception as e:
            logger.error("Agent '%s': Function '%s': Error in entry_node: %s", self.agent_name, func_name, e, exc_info=True)
            raise
        
        logger.debug("Agent '%s': Exiting function '%s' with state: %s", self.agent_name, func_name, state)
        return state

    @record_node(ArchitectNodeEnum.GENERATE_REQUIREMENTS)
    @handle_errors_and_reset
    def generate_requirements_document_node(self, state: ArchitectState) -> ArchitectState:
        """
        Generates the requirements document by sequentially executing generation steps.
        
        For each generation step this node invokes the corresponding LLM prompt, updates 
        the requirements document in the state, and logs the progress.

        Args:
            state (ArchitectState): The current state of the architect, including user input and task details.
        
        Returns:
            ArchitectState: The updated state after processing all generation steps.
        """
        func_name = "generate_requirements_document_node"
        logger.info("Agent '%s': Starting function '%s'.", self.agent_name, func_name)

        generation_steps: Dict[str, GenerationStepConfig] = {
            'project_summary': GenerationStepConfig(
                prompt=self.prompts.project_summary_prompt,
                response_model=TaskResponse,
                input_params={
                    'user_request': state.user_prompt,
                    'task_description': state.current_task.description,
                }
            ),
            'system_architecture': GenerationStepConfig(
                prompt=self.prompts.system_architecture_prompt,
                response_model=TaskResponse,
                input_params={
                    'project_overview': state.requirements_document.project_summary,
                }
            ),
            'file_structure': GenerationStepConfig(
                prompt=self.prompts.file_structure_prompt,
                response_model=TaskResponse,
                input_params={
                    'project_overview': state.requirements_document.project_summary,
                    'system_architecture': state.requirements_document.system_architecture
                }
            ),
            'microservice_design': GenerationStepConfig(
                prompt=self.prompts.microservice_design_prompt,
                response_model=TaskResponse,
                input_params={
                    'project_overview': state.requirements_document.project_summary,
                    'system_architecture': state.requirements_document.system_architecture
                }
            ),
            'tasks_summary': GenerationStepConfig(
                prompt=self.prompts.tasks_summary_prompt,
                response_model=TaskResponse,
                input_params={
                    'project_overview': state.requirements_document.project_summary,
                    'system_architecture': state.requirements_document.system_architecture,
                    'microservice_design': state.requirements_document.microservice_design
                }
            ),
            'code_standards': GenerationStepConfig(
                prompt=self.prompts.code_standards_prompt,
                response_model=TaskResponse,
                input_params={
                    'user_request': state.user_prompt,
                    'user_requested_standards': state.requested_standards,
                }
            ),
            'implementation_plan': GenerationStepConfig(
                prompt=self.prompts.implementation_details_prompt,
                response_model=TaskResponse,
                input_params={
                    'system_architecture': state.requirements_document.system_architecture,
                    'microservice_design': state.requirements_document.microservice_design,
                    'file_structure': state.requirements_document.file_structure,
                }
            ),
            'license_terms': GenerationStepConfig(
                prompt=self.prompts.license_details_prompt,
                response_model=TaskResponse,
                input_params={
                    'user_request': state.user_prompt,
                    'license_text': state.license_header,
                }
            )
        }

        for step_name, config in generation_steps.items():
            logger.info(
                "[%s] Agent '%s': In function '%s' - Starting processing step '%s'.",
                func_name, self.agent_name, func_name, step_name
            )

            llm_output = self.invoke_with_pydantic_model(
                config.prompt,
                config.input_params,
                config.response_model
            )

            content = llm_output.response.content
            setattr(state.requirements_document, step_name, content)

            logger.info(
                "[%s] Agent '%s': Completed processing step '%s'.",
                func_name, self.agent_name, step_name
            )

        logger.info("Agent '%s': Completed function '%s'.", self.agent_name, func_name)
        state.current_mode_stage = DocumentGenerationStage.EXTRACT_TASKS
        return state

    @record_node(ArchitectNodeEnum.EXTRACT_TASKS)
    @handle_errors_and_reset
    def extract_tasks_node(self, state: ArchitectState) -> ArchitectState:
        """
        Extracts tasks from the task summary markdown contained in the requirements document
        and converts them into a structured task list.

        This node performs the following:
            - Reads the task summary markdown generated in a previous step.
            - Converts the markdown into a list of task descriptions.
            - Builds a TaskQueue using the build_task_queue helper.
            - Updates the state with the resulting TaskQueue.
            - Transitions the state to the next stage (SAVE_REQUIREMENTS).

        Args:
            state (ArchitectState): The current state of the architect, including the requirements document.

        Returns:
            ArchitectState: The updated state with the extracted task list.
        """
        func_name = "extract_tasks_node"
        logger.info("Agent '%s': Starting function '%s'.", self.agent_name, func_name)

        tasks_summary = state.requirements_document.tasks_summary
        
        llm_output = self.invoke_with_pydantic_model(
            self.prompts.tasks_extraction_prompt,
            {
                'tasks_summary': tasks_summary
            },
            TaskList
        )

        task_descriptions = llm_output.response.tasks
        logger.info("Extracted %d tasks from the prompt output.", len(task_descriptions))

        processed_tasks = self._build_task_queue(task_descriptions)
        state.tasks.extend(processed_tasks)
        logger.info("Agent '%s': Added %d tasks to the state.", self.agent_name, len(processed_tasks))

        state.current_mode_stage = DocumentGenerationStage.SAVE_REQUIREMENTS
        logger.info("Agent '%s': Updated mode stage to SAVE_REQUIREMENTS.", self.agent_name)
    
        return state

    @record_node(ArchitectNodeEnum.SAVE_REQUIREMENTS)
    @handle_errors_and_reset
    def save_requirements_document_node(self, state: ArchitectState) -> ArchitectState:
        """
        Writes the requirements document to the local filesystem.

        This node performs the following:
            - Retrieves the requirements document from the state and converts it to Markdown.
            - Writes the document to a file using a well-defined file name and path.
            - Updates the state with the result of the file-writing operation.
            - Transitions the state to the next stage (GATHER_PROJECT_DETAILS).

        Args:
            state (ArchitectState): The current state of the architect.

        Returns:
            ArchitectState: The updated state of the architect.
        """
        func_name = "save_requirements_document_node"
        logger.info("Agent '%s': Starting function '%s'.", self.agent_name, func_name)
        
        requirements_document = state.requirements_document.to_markdown()
        logger.debug("Agent '%s': Requirements document (Markdown) length: %d characters.",
                self.agent_name, len(requirements_document))
    
        REQ_DOC_PATH = path.join(state.project_directory, "docs", "requirements_document.md")
        logger.debug("Agent '%s': File path for requirements document: %s", self.agent_name, REQ_DOC_PATH)
    
        write_failed, msg = CodeFileWriter.write_generated_code_to_file.invoke({
            'generated_code': requirements_document,
            'file_path': REQ_DOC_PATH
        })

        if not write_failed:
            logger.info("Agent '%s': Requirements document successfully written to %s.", self.agent_name, REQ_DOC_PATH)
        else:
            logger.error("Agent '%s': Failed to write requirements document. Message: %s", self.agent_name, msg)
        
        state.current_mode_stage = DocumentGenerationStage.GATHER_PROJECT_DETAILS
        logger.info("Agent '%s': Updated mode stage to GATHER_PROJECT_DETAILS.", self.agent_name)
    
        return state

    @record_node(ArchitectNodeEnum.GATHER_PROJECT_DETAILS)
    @handle_errors_and_reset
    def gather_project_details_node(self, state: ArchitectState) -> ArchitectState:
        """
        Gathers project details by invoking an LLM prompt and updating the state.

        This node performs the following:
            - Invokes the project details prompt using the LLM with the original user input.
            - Updates the state with the generated project name.
            - Marks that project details have been provided and sets the current task's status to DONE.
            - Transitions the workflow stage to FINISHED.

        Args:
            state (ArchitectState): The current state of the architect, including user input and the requirements document.

        Returns:
            ArchitectState: The updated state with project details.
        """
        func_name = "gather_project_details_node"
        logger.info("Agent '%s': Starting function '%s'.", self.agent_name, func_name)
        logger.debug("Agent '%s': User prompt: %s", self.agent_name, state.user_prompt)

        llm_output = self.invoke_with_pydantic_model(
            self.prompts.gather_project_details_prompt,
            {
                'user_request': state.user_prompt
            },
            ProjectDetails
        )
        logger.debug("Agent '%s': LLM output received: %s", self.agent_name, llm_output.response)

        project_details = llm_output.response
        state.project_name = project_details.project_name
        logger.info("Agent '%s': Project name extracted: %s", self.agent_name, state.project_name)

        state.current_mode_stage = DocumentGenerationStage.FINISHED
        logger.info("Agent '%s': Updated mode stage to FINISHED.", self.agent_name)

        return state

    @record_node(ArchitectNodeEnum.EXIT)
    def exit_node(self, state: ArchitectState) -> ArchitectOutput:
        """
        Finalizes the workflow by performing any necessary cleanup and updating the state.
        
        For DOCUMENT_GENERATION mode, if the current mode stage is FINISHED, 
        it marks the current task as DONE.
        
        Args:
            state (ArchitectState): The current state of the architect.
            
        Returns:
            ArchitectOutput: The final output state.
        """
        func_name = "exit_node"
        logger.info("Agent '%s': %s - Entering exit node.", self.agent_name, func_name)
        
        if state.operational_mode == ArchitectAgentMode.DOCUMENT_GENERATION:
            logger.debug("Agent '%s': %s - Operational mode is DOCUMENT_GENERATION. Current mode stage: %s", 
                     self.agent_name, func_name, state.current_mode_stage)
            if state.current_mode_stage == DocumentGenerationStage.FINISHED:
                state.current_task.task_status = Status.DONE
                logger.info("Agent '%s': %s - Task status set to DONE.", self.agent_name, func_name)
            else:
                state.current_task.task_status = Status.INCOMPLETE
                logger.warning("Agent '%s': %s - Exit node reached but current_mode_stage is not FINISHED (current stage: %s). Task status set to INCOMPLETE.", 
                            self.agent_name, func_name, state.current_mode_stage)
        
        logger.info("Agent '%s': %s - Exiting workflow (exit node).", self.agent_name, func_name)
        return state

    def _build_task_queue(self, task_descriptions: list) -> TaskQueue:
        """
        Constructs a TaskQueue from a list of task descriptions.

        Args:
            task_descriptions (list): A list of strings where each string is a description of a task.

        Returns:
            TaskQueue: A queue containing Task objects created from the descriptions.
        """
        logger.info(f"{self.agent_name}: Building task queue from {len(task_descriptions)} task descriptions.")
        task_queue: TaskQueue = TaskQueue()
        for description in task_descriptions:
            logger.debug(f"{self.agent_name}: Creating task from description: {description}")
            task_queue.add_item(Task(
                description=description,
                task_status=Status.NEW
            ))
        logger.info(f"{self.agent_name}: Task queue built with {len(task_queue)} tasks.")
        return task_queue
