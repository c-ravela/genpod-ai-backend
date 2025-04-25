# reviewer_work_flow.py
import subprocess
from os import getcwd, path, chdir, makedirs

from agents.reviewer._internal.reviewer_mode_enum import (ReviewerMode,
                                                          ReviewStage)
from agents.reviewer._internal.reviewer_node_enum import ReviewerNodeEnum
from agents.reviewer._internal.reviewer_prompt import ReviewerPrompts
from agents.reviewer._internal.reviewer_state import (ReviewerOutput,
                                                      ReviewerState)
from core.decorators import handle_errors_and_reset, record_node
from core.workflow import BaseWorkFlow
from llms.llm import LLM
from models import (FilePathSelectionResponse, IssuesReport, FileIssue, Issue, IssuesQueue,
                    LanguageSelectionResponse, Status)
from tools.docker_sandbox import (docker_sandbox_description,
                                  docker_sandbox_executor)
from utils.logger import logger
from utils.yaml_utils import read_yaml
from typing import List

CHECKS_CONFIG_PATH = path.join(getcwd(), "agents", "reviewer" ,"checks.yaml")
LANGUAGE_TOOLS_CONFIG_PATH = path.join(getcwd(), "agents", "reviewer", "reviewer_tools.yml")
    
class ReviewerWorkFlow(BaseWorkFlow[ReviewerPrompts]):
    """
    Implements the workflow for the code review agent.

    This workflow:
      - Loads check configuration from a YAML file.
      - Executes all checks sequentially (each must pass before moving on).
      - Stops further checks if any check reports errors.
    """

    def __init__(self, agent_id: str, agent_name: str, llm: LLM, use_rag: bool):
        """
        Initializes the ReviewerWorkFlow.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Human-readable name of the agent.
            llm (LLM): Instance of the language model.
            use_rag (bool): Flag indicating whether to use Retrieval-Augmented Generation.
            checks_config_path (str): Absolute path to the YAML configuration file for checks.
        """
        super().__init__(agent_id, agent_name, ReviewerPrompts(use_rag), llm, use_rag)
        self.checks_config_path = CHECKS_CONFIG_PATH
        self.checks_config = self._load_checks_config()
        self._is_git_initialized = False

    def _load_checks_config(self) -> dict:
        """
        Loads the checks configuration from the specified YAML file.
        
        Expected YAML structure:
        
            checks:
              - name: "static_code_analysis"
                order: 1
                description: "Perform static code analysis using Semgrep."
              - name: "lint_check"
                order: 2
                description: "Run linting tools (e.g., flake8) to check code style."
              - name: "test_execution"
                order: 3
                description: "Execute unit tests using pytest."
        
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

        Updated Flow:
        0. Determine the programming language by invoking an LLM using a language selection prompt.
            - If no matching language is found (LLM outputs "none"), log an error and exit.
        1. Load the language tools configuration from a YAML file (e.g., language_tools.yml).
        2. Retrieve and sort checks from the checks configuration.
        3. For each enabled check:
            a. Use the check name (as defined in checks.yaml) directly to identify the tool type.
            b. Retrieve the corresponding tool details for the selected language.
            c. Format the command by substituting placeholders (e.g. {project_directory} for static analysis or {file_path} for lint/test).
            d. Execute the check in a Docker sandbox using the selected tool's dockerfile and volume mapping.
            e. Build an IssuesReport from the raw output via the generic check issue report prompt.
            f. If any issues are reported, add them to state.issues and halt further checks.
        """
        # --- Step 0: Select Programming Language ---
        # Load the language tools configuration from YAML.
        language_tools = read_yaml(LANGUAGE_TOOLS_CONFIG_PATH)
        logger.info(f"{self.agent_name}: Loaded language tools configuration from {LANGUAGE_TOOLS_CONFIG_PATH}")

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

        # If the LLM returns "unknown", then no matching language was found.
        if selected_language == "unknown" or selected_language not in language_tools.get("languages", {}):
            logger.error(f"{self.agent_name}: No matching programming language found based on the requirements. Current reviewer agent is unable to run checks.")
            return state

        # --- Step 1: Retrieve and sort checks ---
        checks = self.checks_config.get("checks", [])
        checks_sorted = sorted(checks, key=lambda chk: chk.get("order", 0))
        logger.info(f"{self.agent_name}: Starting execution of {len(checks_sorted)} checks.")

        # --- Iterate over each check ---
        for chk in checks_sorted:
            check_name = chk.get("name")
            check_description = chk.get("description")

            if not chk.get("enabled", True):
                logger.info(f"{self.agent_name}: Skipping disabled check '{check_name}'.")
                continue

            logger.info(f"{self.agent_name}: Executing check '{check_name}': {check_description}")

            # --- Retrieve tool details using the check name as key. ---
            tool_details = language_tools["languages"].get(selected_language, {}).get(check_name.lower())
            if not tool_details:
                logger.error(f"{self.agent_name}: No tool configuration found for language '{selected_language}' and check '{check_name}'. Skipping check.")
                continue
            
            working_dir = tool_details.get("working_dir", "/app")
            # --- Step 3: Format the command ---
            # For static analysis, use {project_directory}; for lint and test phases, use {file_path}.
            if check_name.lower() == "static_analysis":
                formatted_command = tool_details["command"].format(project_directory=working_dir)
            else:
                # --- Step 4: Determine the file path using LLM ---
                # Execute "ls -la" on the project directory to provide the LLM with available file information.
                # (For simplicity, assume `directory_listing` is obtained via an appropriate method.)
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

            # Retrieve libraries directly from tool_details (if provided).
            libraries = tool_details.get("libraries", None)

            # --- Step 4: Execute the Check in Docker Sandbox ---
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
                continue  # Log error and move on to the next check.

            # --- Step 5: Build IssuesReport from the Raw Output ---
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
            logger.info(f"{self.agent_name}: Issues report for check '{check_name}' contains {len(issues_report.file_issues)} issues.")

            # --- Step 6: Fix file paths in the issues from container to local filesystem ---
            if issues_report.file_issues:
                issues_report.file_issues = self._map_container_to_local_paths(
                    issues_report.file_issues,
                    state,
                    container_working_dir=working_dir
                )

            # --- Step 7: Determine Whether to Halt or Continue ---
            if issues_report.file_issues:
                issues: IssuesQueue = self._prepare_issues(issues_report)
                logger.info(f"{self.agent_name}: Prepared {len(issues)} issues from static code analysis.")

                state.issues.extend(issues)
                logger.warning(f"{self.agent_name}: Check '{check_name}' reported issues. Stopping further checks.")
                break
            else:
                logger.info(f"{self.agent_name}: Check '{check_name}' passed with no reported issues.")

        state.current_mode_stage = ReviewStage.FINISHED
        logger.info(f"{self.agent_name}: Completed execution of review checks. Setting stage to FINISHED.")
        return state

    @record_node(ReviewerNodeEnum.EXIT)
    def exit_node(self, state: ReviewerState) -> ReviewerOutput:
        """
        Finalizes the review workflow by marking the review as complete.
        """
        if state.operational_mode == ReviewerMode.UNDER_REVIEW:
            if state.current_mode_stage == ReviewStage.FINISHED:
                state.current_task.task_status = Status.DONE
                logger.info(f"{self.agent_name}: Review completed. Task marked as DONE.")
            else:
                logger.warning(f"{self.agent_name}: Review incomplete. Task marked as INCOMPLETE.")
                state.current_task.task_status = Status.INCOMPLETE
        else:
            logger.warning(f"{self.agent_name}: Operational mode not UNDER_REVIEW. Task status unchanged.")
        
        logger.info(f"{self.agent_name}: Exiting workflow. Total issues recorded: {len(state.issues)}.")
        return state

    def router(self, state: ReviewerState) -> str:
        """
        Routes the state to the next node based on the current stage.
        """
        logger.debug(f"{self.agent_name}: Routing state with stage: {state.current_mode_stage}")
        if state.current_mode_stage == ReviewStage.RUN_CHECKS:
            return str(ReviewerNodeEnum.RUN_CHECKS)
        elif state.current_mode_stage == ReviewStage.FINISHED:
            return str(ReviewerNodeEnum.EXIT)
        return str(ReviewerNodeEnum.EXIT)

    @staticmethod
    def _get_directory_listing(directory: str) -> str:
        """
        Returns the output of the `tree` command executed on the provided directory.
        
        Args:
            directory (str): The directory path to list.
        
        Returns:
            str: The output of the "tree" command or an empty string if an error occurs.
        """
        try:
            # Using `tree -a` to list all files/directories including hidden ones.
            output = subprocess.check_output(["tree", "-a"], cwd=directory, text=True)
            return output
        except Exception as e:
            # Optionally, log the error here
            return ""

    def _map_container_to_local_paths(
        self, 
        file_issues: List[FileIssue], 
        state: ReviewerState, 
        container_working_dir: str
    ) -> List[FileIssue]:
        """
        Given a list of FileIssues whose file paths are reported from within the container
        (e.g., "/app/..."), this method maps these paths to their corresponding local filesystem
        paths based on the review state.
        
        Args:
            file_issues (List[FileIssue]): The original file issues with container paths.
            state (ReviewerState): The current review state containing the local project directory.
            container_working_dir (str): The working directory inside the container (e.g., "/app").
        
        Returns:
            List[FileIssue]: Updated list of file issues with file paths mapped to the local filesystem.
        """
        local_root = path.join(state.project_directory, state.project_name)
        updated_issues = []
        for issue in file_issues:
            # If the file path in issue starts with the container working dir, replace it.
            if issue.file_path.startswith(container_working_dir):
                # Replace only the first occurrence.
                issue.file_path = issue.file_path.replace(container_working_dir, local_root, 1)
            updated_issues.append(issue)
        return updated_issues

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
        makedirs(self.project_path, exist_ok=True)
        try:
            chdir(self.project_path)
            if not path.isdir(".git"):
                logger.info(f"{self.agent_name}: Initializing Git in the project directory.")
                subprocess.run(["git", "init"], check=True)

            self._is_git_initialized = True
        except Exception as e:
            logger.error(f"{self.agent_name}: Error during Git initialization: {e}")
        finally:
            chdir("..")

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
