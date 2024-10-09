"""
"""
import os

from agents.agent.agent import Agent
from agents.reviewer.reviewer_state import ReviewerState
from llms.llm import LLM
from models.constants import Status
from models.models import Issue, IssuesQueue
from models.reviewer_models import ReviewerOutput
from prompts.reviewer_prompts import ReviewerPrompts
from tools.semgrep import Semgrep
from utils.logs.logging_utils import logger


class ReviewerAgent(Agent[ReviewerState, ReviewerPrompts]):
    """
    The ReviewerAgent class is responsible for conducting comprehensive code reviews, including code quality analysis, 
    security analysis, linting, and documentation checks. It identifies bugs, vulnerabilities, inconsistencies, 
    and missing documentation in the codebase and generates issues based on the findings.

    The ReviewerAgent follows a structured, multi-step process to thoroughly analyze codebases. 
    At each stage—whether it involves code quality checks, security assessments, linting, or 
    documentation verification—if an issue is detected, the agent halts the review process and 
    escalates the issue to the supervisor for resolution. This ensures that problems are addressed 
    immediately. To optimize resource usage and minimize unnecessary computational costs, the agent 
    stops further analysis upon identifying an issue, preventing redundant operations and conserving 
    resources.
    """

    # names of the graph node
    entry_node_name: str
    static_code_analysis_node_name: str
    update_state_node_name: str

    project_path: str
    error_message: str

    def __init__(self, agent_id: str, agent_name: str, llm: LLM) -> None:
        """
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
        
        self.error_message = ""

    def prepare_issues(self, output: ReviewerOutput) -> IssuesQueue:
        """
        prepares queue of issues.
        """
        logger.info(f"----{self.agent_name}: preparing issues----")

        issues: IssuesQueue = IssuesQueue()
        for file_issue in output.file_issues:
            issue: Issue = Issue(
                issue_status=Status.NEW,
                file_path=file_issue.file_path,
                line_number=file_issue.line_number,
                description=file_issue.description,
                suggestions=file_issue.suggestions
            )

            issues.add_item(issue)

        return issues
                    
    def router(self, state: ReviewerState) -> str:
        """
        """
        # This router is triggered after each analysis node invocation.
        # If any issues are found, the Reviewer process halts to address and resolve them.
        # It is inefficient to run all types of analysis in every review cycle because 
        # if an issue is encountered early (e.g., at step 1) and we continue with the 
        # other analyses before resolving it, we waste computational resources.
        # Halting the process as soon as an issue is detected is the most efficient approach, 
        # as even small changes require a complete re-analysis once the issue is resolved.

        if len(state['issues']) > 0:
            logger.info(f"----{self.agent_name}: Found some issues reporting them to supervisor.----")
            return self.update_state_node_name

        return self.update_state_node_name
    
    def entry_node(self, state: ReviewerState) -> ReviewerState:
        """
        """
        logger.info(f"----{self.agent_name}: at entry node----")

        state['issues'] = IssuesQueue()
        self.project_path = os.path.join(state['project_path'], state['project_name'])

        return state
    
    # TODO: Each and every analysis node has to be assigned with priority id
    # Factors to consider:
    #   amount of token that prompt and response might consume
    #   most major changes can happen due to analysis
    #   
    def static_code_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        We use semgrep to do static code analysis.
        """
        logger.info(f"----{self.agent_name}: Performing Static code Analysis on the generated project located at {self.project_path}----")

        sg = Semgrep()

        # TODO: For now we are only doing simple scan but later we need to enhance this with
        # Pro rules scan.
        # Reasons: One we need to login to get access to pro rules analysis, other there has 
        # to be proper git repo setuped at the project location for semgrep to work properly.
        result = sg.simple_scan(self.project_path)

        while True:
            try:
                llm_output = self.llm.invoke_with_pydantic_model(self.prompts.static_code_analysis_prompt, {
                    'static_analysis_tool': sg.name(), 
                    'tool_result': result,
                    'error_message': self.error_message
                }, ReviewerOutput)

                validated_response = llm_output.response
                
                self.error_message = ""
                break # while loop exit
            except Exception as e:
                logger.error(f"----{self.agent_name}: encountered an exception {e}----")
                self.error_message = e
        
        issues: IssuesQueue = self.prepare_issues(validated_response)
        state['issues'].extend(issues)

        return state

    def package_dependencies_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        """

        return state

    def project_requirement_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        """
        
        return state

    def genval_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        """

        return state

    def unit_test_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        """

        return state

    def linting_analysis_node(self, state: ReviewerState) -> ReviewerState:
        """
        """

        return state
