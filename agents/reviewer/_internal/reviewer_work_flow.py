import os
import subprocess

from agents.reviewer._internal.reviewer_mode_enum import (ReviewerMode,
                                                          ReviewStage)
from agents.reviewer._internal.reviewer_node_enum import ReviewerNodeEnum
from agents.reviewer._internal.reviewer_prompt import ReviewerPrompts
from agents.reviewer._internal.reviewer_state import (ReviewerOutput,
                                                      ReviewerState)
from core.decorators import (handle_errors_and_reset, record_node,
                             route_on_errors)
from core.workflow import BaseWorkFlow
from llms.llm import LLM
from models import Issue, IssuesQueue, IssuesReport, Status
from tools.semgrep import Semgrep
from utils.logger import logger


class ReviewerWorkFlow(BaseWorkFlow[ReviewerPrompts]):
    """
    Implements the workflow for a code review agent, orchestrating various nodes (entry,
    static analysis, and exit) based on the current state of the review.

    This workflow leverages an LLM for processing static analysis results, prepares issue
    reports, and updates the state accordingly.
    """    
    def __init__(self, agent_id: str, agent_name: str, llm: LLM, use_rag: bool):
        """
        Initializes the ReviewerWorkFlow with the agent details and LLM instance.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Name of the agent.
            llm (LLM): An instance of the language model to be used.
            use_rag (bool): Flag indicating whether Retrieval-Augmented Generation is enabled.
        """
        super().__init__(agent_id, agent_name, ReviewerPrompts(use_rag), llm, use_rag)
        self.project_path = ""

    @route_on_errors
    def router(self, state: ReviewerState) -> str:
        """
        Routes the current state to the appropriate workflow node based on the operational mode
        and current review stage.

        Args:
            state (ReviewerState): The current state of the reviewer.

        Returns:
            str: The node identifier to which the workflow should route next.
        """
        logger.debug(
            f"{self.agent_name}: Routing state with mode '{state.operational_mode}' "
            f"and stage '{state.current_mode_stage}'"
        )
        if state.operational_mode == ReviewerMode.UNDER_REVIEW:
            if state.current_mode_stage == ReviewStage.STATIC_ANALYSIS:
                return str(ReviewerNodeEnum.STATIC_CODE_ANALYSIS)
            elif state.current_mode_stage == ReviewStage.FINISHED:
                return str(ReviewerNodeEnum.EXIT)

        return str(ReviewerNodeEnum.EXIT)

    @record_node(ReviewerNodeEnum.ENTRY)
    def entry_node(self, state: ReviewerState) -> ReviewerState:
        """
        Entry node to initialize the project environment by setting the project path and
        ensuring the Git repository is ready.

        The method sets the project path, configures the operational mode and current stage,
        and initializes Git if it is not already set up.

        Args:
            state (ReviewerState): The current state of the reviewer, including 'project_directory'
                                   and 'project_name'.

        Returns:
            ReviewerState: The updated state after initialization.
        """
        self.project_path = os.path.join(state.project_directory, state.project_name)
        logger.info(
            f"{self.agent_name}: Entry node initialized. Project path set to '{self.project_path}'."
        )
        state.issues.clear()
        state.operational_mode = ReviewerMode.UNDER_REVIEW
        state.current_mode_stage = ReviewStage.STATIC_ANALYSIS

        logger.info(f"{self.agent_name}: Initializing Git repository if necessary.")
        self._initialize_git()
        return state

    @record_node(ReviewerNodeEnum.STATIC_CODE_ANALYSIS)
    @handle_errors_and_reset
    def static_code_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        Performs static code analysis using Semgrep and updates the reviewer state with the
        discovered issues.

        This method performs a simple Semgrep scan on the project, invokes the LLM to process
        the scan results, and then extracts and appends any issues to the reviewer's state.

        Args:
            state (ReviewerState): The current state of the reviewer, including any pre-existing
                                   error messages and issues.

        Returns:
            ReviewerState: The updated state after performing static code analysis.
        """
        logger.info(f"{self.agent_name}: Performing static code analysis at '{self.project_path}'.")
        semgrep = Semgrep()
        semgrep_scan_result = semgrep.simple_scan(self.project_path)
        logger.debug(f"{self.agent_name}: Semgrep scan result obtained.")

        llm_response = self.invoke_with_pydantic_model(
            self.prompts.static_code_analysis_prompt,
            {   
                'project_name': state.project_name,
                'project_directory': state.project_directory,
                'static_analysis_tool': semgrep.name(),
                'tool_result': semgrep_scan_result,
                'error_message': state.error_message
            },
            IssuesReport
        )
        logger.debug(f"{self.agent_name}: Received LLM response for static code analysis.")

        issues_report = llm_response.response
        issues: IssuesQueue = self._prepare_issues(issues_report)
        logger.info(f"{self.agent_name}: Prepared {len(issues)} issues from static code analysis.")

        state.issues.extend(issues)
        state.current_mode_stage = ReviewStage.FINISHED
        logger.info(f"{self.agent_name}: Static code analysis completed; stage set to '{state.current_mode_stage}'.")

        return state

    @record_node(ReviewerNodeEnum.EXIT)
    def exit_node(self, state: ReviewerState) -> ReviewerOutput:
        """
        Finalizes the review workflow by marking the current task as completed and generating
        the final review output.

        The method updates the task status to 'DONE' and returns a ReviewerOutput object that
        encapsulates the issues found during the review process.

        Args:
            state (ReviewerState): The current state of the reviewer.

        Returns:
            ReviewerOutput: The final output of the review process containing the issues report.
        """
        logger.info(f"{self.agent_name}: Exiting workflow. Finalizing task and generating output.")

        if state.operational_mode == ReviewerMode.UNDER_REVIEW:
            if state.current_mode_stage == ReviewStage.FINISHED:
                state.current_task.task_status = Status.DONE
                logger.info(f"{self.agent_name}: Review stage is finished. Task marked as DONE.")
            else:
                logger.warning(f"{self.agent_name}: Review stage is not finished. Marking task as INCOMPLETE.")
                state.current_task.task_status = Status.INCOMPLETE
        else:
            logger.warning(f"{self.agent_name}: Operational mode is not UNDER_REVIEW. Task status remains unchanged.")

        logger.info(f"{self.agent_name}: Workflow exit complete. Total issues reported: {len(state.issues)}.")

        # New changes: Call the documentation tool only if no issues are reported.
        if len(state.issues) == 0:
            self._trigger_documentation_tool(state)
        else:
            logger.info(f"{self.agent_name}: Issues reported; skipping documentation tool call.")

        return state

    def _initialize_git(self) -> None:
        """
        Initializes a Git repository in the project directory if one does not already exist.

        This method ensures that the project directory exists, changes into that directory,
        checks for the existence of a Git repository by looking for a ".git" folder, and initializes
        a new repository using 'git init' if necessary. The original working directory is restored
        after the operation completes.

        Raises:
            subprocess.CalledProcessError: If the Git initialization command fails.
        """
        os.makedirs(self.project_path, exist_ok=True)
        try:
            os.chdir(self.project_path)
            if not os.path.isdir(".git"):
                logger.info(f"{self.agent_name}: Initializing Git in the project directory.")
                subprocess.run(["git", "init"], check=True)
        except Exception as e:
            logger.error(f"{self.agent_name}: Error during Git initialization: {e}")
        finally:
            os.chdir("..")

    def _prepare_issues(self, output: IssuesReport) -> IssuesQueue:
        """
        Prepares a queue of issues based on the output from the analysis.

        Args:
            output (IssuesReport): Validated response containing detected issues.

        Returns:
            IssuesQueue: Queue of issues prepared for further processing.
        """
        logger.info(f"{self.agent_name}: Preparing issues from analysis results")
        issues = IssuesQueue()

        for file_issue in output.file_issues:
            issue = Issue(
                issue_status=Status.NEW,
                file_path=file_issue.file_path,
                line_number=file_issue.line_number,
                description=file_issue.description,
                suggestions=file_issue.suggestions
            )
            issues.add_item(issue)
            logger.debug(f"{self.agent_name}: Added issue: {issue}")

        return issues

    def package_dependencies_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        Analyzes package dependencies for security and quality.
        """
        logger.info(f"{self.agent_name}: Analyzing package dependencies")
        # Future implementation
        return state

    def project_requirement_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        Analyzes project requirements to ensure they are met.
        """
        logger.info(f"{self.agent_name}: Analyzing project requirements")
        # Future implementation
        return state

    def genval_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        Performs general validation analysis on the codebase.
        """
        logger.info(f"{self.agent_name}: Performing general validation analysis")
        # Future implementation
        return state

    def unit_test_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        Analyzes unit tests to ensure quality coverage.
        """
        logger.info(f"{self.agent_name}: Analyzing unit tests for quality and coverage")
        # Future implementation
        return state

    def linting_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        Performs linting on the codebase to ensure adherence to style guidelines.
        """
        logger.info(f"{self.agent_name}: Performing linting analysis")
        # Future implementation
        return state

    def _trigger_documentation_tool(self, state: ReviewerState) -> None:
        """
        Private method that calls the GenerateProjectDocumentationTool.
        The project path is constructed as the combination of state.project_directory and state.project_name.
        The tool is called only when there are no reviewer issues.
        """
        project_path = os.path.join(state.project_directory, state.project_name)
        logger.info(f"{self.agent_name}: Triggering project documentation tool for project path: {project_path}")
        from tools.generate_project_documentation_tool import GenerateProjectDocumentationTool
        doc_tool = GenerateProjectDocumentationTool()
        try:
            result = doc_tool.run(project_path)
            logger.info(f"{self.agent_name}: Documentation tool result: {result}")
        except Exception as e:
            logger.error(f"{self.agent_name}: Error calling documentation tool: {e}", exc_info=True)
