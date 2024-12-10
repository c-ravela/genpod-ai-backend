"""
"""
import os
import subprocess

from agents.base.base_agent import BaseAgent
from agents.reviewer.reviewer_state import ReviewerState
from llms.llm import LLM
from models.constants import Status
from models.models import Issue, IssuesQueue
from models.reviewer_models import ReviewerOutput
from prompts.reviewer_prompts import ReviewerPrompts
from tools.semgrep import Semgrep
from utils.logs.logging_utils import logger


class ReviewerAgent(BaseAgent[ReviewerState, ReviewerPrompts]):
    """
    The ReviewerAgent class is responsible for conducting comprehensive code reviews,
    including code quality analysis, security analysis, linting, and documentation 
    checks. It identifies bugs, vulnerabilities, inconsistencies, and missing documentation
    in the codebase and generates issues based on the findings.

    The ReviewerAgent follows a structured, multi-step process to thoroughly analyze 
    codebases. At each stage—whether it involves code quality checks, security assessments,
    linting, or documentation verification—if an issue is detected, the agent halts the 
    review process and escalates the issue to the supervisor for resolution. This ensures 
    that problems are addressed immediately. To optimize resource usage and minimize 
    unnecessary computational costs, the agent stops further analysis upon identifying an
    issue, preventing redundant operations and conserving resources.
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        llm: LLM
    ) -> None:
        """
        Initializes the ReviewerAgent with its state, prompts, and necessary configurations.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_name (str): Name of the agent.
            llm (LLM): The language model for processing prompts.
        """
        super().__init__(
            agent_id,
            agent_name,
            ReviewerState(),
            ReviewerPrompts(),
            llm
        )

        self.entry_node_name = "entry"
        self.static_code_analysis_node_name = "static code analysis"
        self.update_state_node_name = "update_state"

        self.project_path = ""

    def prepare_issues(self, output: ReviewerOutput) -> IssuesQueue:
        """
        Prepares a queue of issues based on the output from the analysis.

        Args:
            output (ReviewerOutput): Validated response containing detected issues.

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
                   
    def router(self, state: ReviewerState) -> str:
        """
        Routes the process based on detected issues.

        If issues are found, the process halts, ensuring efficient handling and avoiding
        redundant analyses.

        Args:
            state (ReviewerState): Current state of the reviewer.

        Returns:
            str: Next node name to be executed.
        """
        logger.info(f"{self.agent_name}: Routing to the next step based on current state")
        
        # This router is triggered after each analysis node invocation.
        # If any issues are found, the Reviewer process halts to address and resolve 
        # them. It is inefficient to run all types of analysis in every review cycle 
        # because if an issue is encountered early (e.g., at step 1) and we continue
        # with the other analyses before resolving it, we waste computational resources.
        #  Halting the process as soon as an issue is detected is the most efficient 
        # approach, as even small changes require a complete re-analysis once the issue
        # is resolved.

        if len(state['issues']) > 0:
            logger.info(f"{self.agent_name}: Issues detected. Halting further analysis and updating state.")
            return self.update_state_node_name

        return self.update_state_node_name
   
    def entry_node(self, state: ReviewerState) -> ReviewerState:
        """
        Entry node to initialize the project path and prepare the environment.

        Ensures that the project directory is set up and initializes Git if not already present.

        Args:
            state (ReviewerState): Current state of the reviewer.

        Returns:
            ReviewerState: Updated state after initialization.
        """
        logger.info(f"{self.agent_name}: Entering entry node")
        state['issues'] = IssuesQueue()
        state['error_message'] = BaseAgent.ensure_value(state['error_message'], "")
        self.project_path = os.path.join(state['project_path'], state['project_name'])

        os.makedirs(self.project_path, exist_ok=True)
        try:
            os.chdir(self.project_path)
            if not os.path.isdir(".git"):
                logger.info(f"{self.agent_name}: Initializing Git in the project directory.")
                subprocess.run(["git", "init"], check=True)
        except Exception as e:
            logger.error(f"{self.agent_name}: Error during Git initialization: {e}")
            state['error_message'] = str(e)
        finally:
            os.chdir("..")

        return state

    # TODO: Each and every analysis node has to be assigned with priority id
    # Factors to consider:
    #   amount of tokens that prompt and response might consume
    #   most major changes can happen due to analysis
    def static_code_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        Performs static code analysis using Semgrep.

        Args:
            state (ReviewerState): Current state of the reviewer.

        Returns:
            ReviewerState: Updated state after analysis.
        """
        logger.info(f"{self.agent_name}: Performing static code analysis at {self.project_path}")
        sg = Semgrep()

        # TODO: For now we are only doing simple scan but later we need to enhance 
        # this with Pro rules scan.
        # Reasons: One we need to login to get access to pro rules analysis, other 
        # there has to be proper git repo setuped at the project location for 
        # semgrep to work properly.

        try:
            result = sg.simple_scan(self.project_path)
            while True:
                try:
                    llm_output = self.llm.invoke_with_pydantic_model(
                        self.prompts.static_code_analysis_prompt, 
                        {
                            'static_analysis_tool': sg.name(),
                            'tool_result': result,
                            'error_message': state['error_message']
                        },
                        ReviewerOutput
                    )
                    validated_response = llm_output.response
                    state['error_message'] = ""
                    break  # while loop exit
                except Exception as e:
                    logger.error(f"{self.agent_name}: Error during LLM invocation: {e}")
                    state['error_message'] = str(e)
       
            issues: IssuesQueue = self.prepare_issues(validated_response)
            state['issues'].extend(issues)
        except Exception as e:
            logger.error(f"Error during static code analysis: {e}")
            state['error_message'] = str(e)

        return state

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
