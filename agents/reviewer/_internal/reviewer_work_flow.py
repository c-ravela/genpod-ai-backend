import re
import subprocess
from difflib import SequenceMatcher
from os import chdir, getcwd, makedirs, path
from typing import List

from agents.reviewer._internal.reviewer_mode_enum import (ReviewerMode,
                                                          ReviewStage)
from agents.reviewer._internal.reviewer_node_enum import ReviewerNodeEnum
from agents.reviewer._internal.reviewer_prompt import ReviewerPrompts
from agents.reviewer._internal.reviewer_state import (ReviewerOutput,
                                                      ReviewerState)
from core.decorators import handle_errors_and_reset, record_node
from core.workflow import BaseWorkFlow
from llms.llm import LLM
from models import (FileIssue, FilePathSelectionResponse, Issue, IssuesQueue,
                    IssuesReport, LanguageSelectionResponse, Status)
from tools.docker_sandbox import (docker_sandbox_description,
                                  docker_sandbox_executor)
from tools.generate_project_documentation import GenerateProjectDocumentationTool
from utils.logger import logger
from utils.yaml_utils import read_yaml

CHECKS_CONFIG_PATH = path.join(getcwd(), "agents", "reviewer", "checks.yaml")
LANGUAGE_TOOLS_CONFIG_PATH = path.join(getcwd(), "agents", "reviewer", "reviewer_tools.yml")


class ReviewerWorkFlow(BaseWorkFlow[ReviewerPrompts]):
    """
    Implements the workflow for the code review agent.

    This workflow:
      - Loads check configuration from a YAML file.
      - Executes all checks sequentially (each must pass before moving on).
      - Deduplicates issues against previous runs and the current run.
      - Stops further checks if any new (non-duplicate) issue is found.
    """

    DUPLICATE_THRESHOLD = 0.8

    def __init__(self, agent_id: str, agent_name: str, llm: LLM, use_rag: bool):
        """
        Initializes the ReviewerWorkFlow.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Human-readable name of the agent.
            llm (LLM): Instance of the language model.
            use_rag (bool): Flag indicating whether to use Retrieval-Augmented Generation.
        """
        super().__init__(agent_id, agent_name, ReviewerPrompts(use_rag), llm, use_rag)
        self.checks_config_path = CHECKS_CONFIG_PATH
        self.checks_config = self._load_checks_config()
        self._is_git_initialized = False

    def _load_checks_config(self) -> dict:
        """
        Loads the checks configuration from the specified YAML file.

        Returns:
            dict: Parsed configuration dictionary.
        """
        try:
            config = read_yaml(self.checks_config_path)
            logger.info("Loaded checks configuration from %s", self.checks_config_path)
            return config
        except Exception as e:
            logger.error("Failed to load checks configuration: %s", e)
            raise

    @record_node(ReviewerNodeEnum.ENTRY)
    def entry_node(self, state: ReviewerState) -> ReviewerState:
        """
        Entry node to initialize the review process.

        Clears previous issues and sets the operational mode and stage.
        """
        # Check if this is a documentation generation task
        if state.is_reviewed and state.current_task.task_status == Status.NEW:
            logger.info(f"{self.agent_name}: Received documentation generation task.")
            state.operational_mode = ReviewerMode.DOCUMENTATION
            self.project_path = path.join(state.project_directory, state.project_name)
            return state

        # Normal review process
        state.issues.clear()
        state.operational_mode = ReviewerMode.UNDER_REVIEW
        state.current_mode_stage = ReviewStage.RUN_CHECKS
        self.project_path = path.join(state.project_directory, state.project_name)
        logger.info(f"{self.agent_name}: Entry node initialized. Review process starting with RUN_CHECKS stage.")

        if not self._is_git_initialized:
            self._initialize_git()

        return state

    @record_node(ReviewerNodeEnum.RUN_CHECKS)
    @handle_errors_and_reset
    def run_checks_node(self, state: ReviewerState) -> ReviewerState:
        """
        Executes all configured review checks sequentially.

        Steps:
          0. Select programming language.
          1. Load and sort checks.
          2. For each enabled check:
             a. Format and run in Docker sandbox.
             b. Generate an IssuesReport.
             c. Deduplicate issues and flag duplicates as ABANDONED.
             d. Halt on first new issue, otherwise continue.
        """
        language_tools = read_yaml(LANGUAGE_TOOLS_CONFIG_PATH)
        logger.info(f"{self.agent_name}: Loaded language tools configuration from {LANGUAGE_TOOLS_CONFIG_PATH}")

        # Step 0: Select Programming Language
        language_selection_response = self.invoke_with_pydantic_model(
            self.prompts.language_selection_prompt,
            {
                "requirements": state.requirements_document.tech_stack,
                "available_languages": str(list(language_tools.get("languages", {}).keys()))
            },
            LanguageSelectionResponse
        )
        selected_language = language_selection_response.response.language.lower()
        logger.info(f"{self.agent_name}: Selected programming language: '{selected_language}'")

        if selected_language == "unknown" or selected_language not in language_tools.get("languages", {}):
            logger.error(f"{self.agent_name}: No matching programming language found based on the requirements. Aborting checks.")
            return state

        # Step 1: Retrieve and sort checks
        checks = self.checks_config.get("checks", [])
        checks_sorted = sorted(checks, key=lambda chk: chk.get("order", 0))
        logger.info(f"{self.agent_name}: Starting execution of {len(checks_sorted)} checks.")

        # Execute checks
        for chk in checks_sorted:
            check_name = chk.get("name")
            check_description = chk.get("description")

            if not chk.get("enabled", True):
                logger.info(f"{self.agent_name}: Skipping disabled check '{check_name}'.")
                continue

            logger.info(f"{self.agent_name}: Executing check '{check_name}': {check_description}")
            tool_details = language_tools["languages"][selected_language].get(check_name.lower())
            if not tool_details:
                logger.error(f"{self.agent_name}: No tool configuration found for check '{check_name}'. Skipping.")
                continue

            working_dir = tool_details.get("working_dir", "/app")
            # Step 2a: Format command
            if check_name.lower() == "static_analysis":
                formatted_command = tool_details["command"].format(project_directory=working_dir)
            else:
                directory_listing = self._get_directory_listing(path.join(state.project_directory, state.project_name))
                check_command = tool_details.get("command") #.replace("{", "<").replace("}", ">")
                check_command_description = tool_details.get("command_description", "")
                file_path_response = self.invoke_with_pydantic_model(
                    self.prompts.file_path_selection_prompt,
                    {
                        "check_name": check_name,
                        "check_description": check_description,
                        "project_directory": working_dir,
                        "directory_listing": directory_listing,
                        "command": check_command,
                        "command_description": check_command_description
                    },
                    FilePathSelectionResponse
                )
                selected_file_path = file_path_response.response.file_path
                formatted_command = tool_details["command"].format(file_path=selected_file_path)

            # Step 2b: Run in Docker sandbox
            libraries = tool_details.get("libraries", None)
            dockerfile = tool_details.get("dockerfile")
            mounts = {working_dir: path.join(state.project_directory, state.project_name)}
            try:
                raw_output = docker_sandbox_executor(
                    dockerfile=dockerfile,
                    source_path=path.join(state.project_directory, state.project_name),
                    language=selected_language,
                    command=formatted_command,
                    libraries=libraries,
                    mounts=mounts
                )
                logger.info(f"{self.agent_name}: Raw output from docker sandbox for check '{check_name}': {raw_output}")
            except Exception as e:
                logger.error(f"{self.agent_name}: Docker sandbox execution error for check '{check_name}': {e}")
                continue

            # Step 2c: Build IssuesReport
            generic_report_response = self.invoke_with_pydantic_model(
                self.prompts.generic_check_issue_report_prompt,
                {
                    "check_name": check_name,
                    "check_description": check_description,
                    "raw_check_output": raw_output
                },
                IssuesReport
            )
            issues_report = generic_report_response.response
            logger.info(f"{self.agent_name}: Issues report for '{check_name}' contains {len(issues_report.file_issues)} issues.")

            # Map paths and dedupe
            issues_report.file_issues = self._map_container_to_local_paths(
                issues_report.file_issues,
                state,
                container_working_dir=working_dir
            )
            # original total before filtering
            total_found = len(issues_report.file_issues)

            if total_found == 0:
                # no issues at all → just continue
                logger.info(
                    f"{self.agent_name}: No issues found for '{check_name}'. Continuing to next check."
                )
                continue

            # prepare only non-duplicates (duplicates increment state.duplicate_counter)
            new_queue = self._prepare_issues(issues_report, state)
            new_count = len(new_queue.items)
            duplicates_count = total_found - new_count

            # Step 2d: Halt on first new issue
            if new_count > 0:
                # add only the fresh issues
                state.issues.extend(new_queue)
                logger.warning(
                    f"{self.agent_name}: Check '{check_name}' reported {new_count} new issues "
                    f"(skipped {duplicates_count} duplicates). Stopping further checks."
                )
                break
            else:
                logger.info(
                    f"{self.agent_name}: All {total_found} issues from '{check_name}' were duplicates "
                    f"(skipped {duplicates_count}). Continuing to next check."
                )
                continue

        state.current_mode_stage = ReviewStage.FINISHED
        logger.info(f"{self.agent_name}: Completed execution of review checks. Setting stage to FINISHED.")
        return state

    @record_node(ReviewerNodeEnum.GENERATE_DOCUMENTATION)
    @handle_errors_and_reset
    def generate_documentation_node(self, state: ReviewerState) -> ReviewerState:
        """
        Node for generating project documentation.
        """
        logger.info(f"{self.agent_name}: Generating project documentation...")

        try:
            project_path = path.join(
                state.project_directory,
                state.project_name or "project"
            )

            doc_tool = GenerateProjectDocumentationTool()
            result = doc_tool._run(project_directory=project_path)

            logger.info(f"{self.agent_name}: Documentation generation completed: {result}")
            state.documentation_generated = True
        except Exception as e:
            logger.error(f"{self.agent_name}: Documentation generation failed: {e}")
            state.documentation_generated = False

        return state

    @record_node(ReviewerNodeEnum.EXIT)
    def exit_node(self, state: ReviewerState) -> ReviewerOutput:
        """
        Finalizes the review workflow by marking the review as complete.
        """
        # If no issues found and not yet marked as reviewed
        if len(state.issues) == 0 and not state.is_reviewed and state.operational_mode == ReviewerMode.UNDER_REVIEW:
            state.is_reviewed = True
            logger.info(f"{self.agent_name}: No issues found, marking as reviewed.")

        # Update task status to DONE
        if state.current_task.task_status != Status.DONE and state.is_reviewed:
            state.current_task.task_status = Status.DONE
            logger.info(f"{self.agent_name}: Task marked as DONE.")
        elif state.operational_mode == ReviewerMode.UNDER_REVIEW:
            if state.current_mode_stage == ReviewStage.FINISHED:
                state.current_task.task_status = Status.DONE
                logger.info(f"{self.agent_name}: Review completed. Task marked as DONE.")
            else:
                logger.warning(f"{self.agent_name}: Review incomplete. Task marked as INCOMPLETE.")
                state.current_task.task_status = Status.INCOMPLETE

        logger.info(f"{self.agent_name}: Exiting workflow. Total issues recorded: {len(state.issues)}.")
        return state

    def router(self, state: ReviewerState) -> str:
        """
        Routes the state to the next node based on the current stage.
        """
        # If in documentation mode, go straight to documentation generation
        if state.operational_mode == ReviewerMode.DOCUMENTATION:
            return str(ReviewerNodeEnum.GENERATE_DOCUMENTATION)
            
        logger.debug(f"{self.agent_name}: Routing state with stage: {state.current_mode_stage}")
        if state.current_mode_stage == ReviewStage.RUN_CHECKS:
            return str(ReviewerNodeEnum.RUN_CHECKS)
        return str(ReviewerNodeEnum.EXIT)

    @staticmethod
    def _get_directory_listing(directory: str) -> str:
        """
        Returns the output of the `tree -a` command for the provided directory,
        or an empty string if an error occurs.
        """
        try:
            return subprocess.check_output(["tree", "-a"], cwd=directory, text=True)
        except Exception:
            return ""

    def _map_container_to_local_paths(
        self,
        file_issues: List[FileIssue],
        state: ReviewerState,
        container_working_dir: str
    ) -> List[FileIssue]:
        """
        Maps file paths from the container to local filesystem paths.
        """
        local_root = path.join(state.project_directory, state.project_name)
        updated = []
        for issue in file_issues:
            if issue.file_path.startswith(container_working_dir):
                issue.file_path = issue.file_path.replace(container_working_dir, local_root, 1)
            updated.append(issue)
        return updated

    def _is_duplicate(self, new_issue: Issue, existing_issue: Issue) -> bool:
        """
        Determines whether `new_issue` is a duplicate of `existing_issue` based on
        file path and fuzzy comparison of descriptions.
        """
        if new_issue.file_path != existing_issue.file_path:
            return False
        def normalize(text: str) -> str:
            txt = re.sub(r"[^\w\s]", "", text.lower())
            return " ".join(txt.split())
        return SequenceMatcher(None, normalize(new_issue.description), normalize(existing_issue.description)).ratio() >= self.DUPLICATE_THRESHOLD

    def _prepare_issues(self, output: IssuesReport, state: ReviewerState) -> IssuesQueue:
        """
        Prepares and deduplicates issues by:
          - returning only new (non-duplicate) issues, and
          - marking any duplicate of an existing issue as ABANDONED on the existing object 
            (incrementing its duplicate_counter).
        """
        seen = list(state.previous_issues.items) + list(state.issues.items)
        new_queue = IssuesQueue()

        for file_issue in output.file_issues:
            new_issue = Issue(
                file_path=file_issue.file_path,
                line_number=file_issue.line_number,
                description=file_issue.description,
                suggestions=file_issue.suggestions
            )

            # Look for an existing matching issue
            duplicate = next(
                (existing for existing in seen if self._is_duplicate(new_issue, existing)),
                None
            )
            if duplicate:
                # Update the existing issue, not the new_issue
                duplicate.issue_status = Status.ABANDONED
                duplicate.duplicate_counter += 1
                if not duplicate.human_reviewed:
                    state.previous_issues.requeue_item(duplicate)
                logger.debug("Duplicate skipped (abandoned): %s", duplicate.issue_details())
            else:
                new_queue.add_item(new_issue)

        return new_queue

    def _initialize_git(self) -> None:
        """
        Initializes a Git repository in the project directory if one does not already exist.
        """
        makedirs(self.project_path, exist_ok=True)
        orig = getcwd()
        try:
            chdir(self.project_path)
            if not path.isdir(".git"):
                logger.info(f"{self.agent_name}: Initializing Git in the project directory.")
                subprocess.run(["git", "init"], check=True)
            self._is_git_initialized = True
        except Exception as e:
            logger.error(f"{self.agent_name}: Error during Git initialization: {e}")
        finally:
            chdir(orig)
