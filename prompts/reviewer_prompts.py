"""
Reviewer Prompts
"""
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from models.reviewer_models import ReviewerOutput


class ReviewerPrompts:
    """
    This class contains prompts used by reviewers.
    """

    static_code_analysis_prompt: PromptTemplate = PromptTemplate(
        template="""
        As a skilled reviewer, you play a crucial role in delivering a comprehensive end-to-end project as per the user's request. 
        Your expertise is in reviewing and analyzing the work done by other team members.

        You have been provided with the output from the `{static_analysis_tool}`.

        Error message will be provided if we encounter an issue with your previous response:
        `{error_message}`

        Tool results:
        ```
        {tool_result}
        ```

        Formatting instructions:
        ```
        {format_instructions}
        ```

        Your task is to generate any issues based on the results provided. Ensure that the issues are clearly detailed and 
        formatted according to the given instructions. Focus solely on project-related issues, excluding any concerns about 
        the tool itself.
        """,
        input_variables= ['static_analysis_tool', 'tool_result', 'error_message'],
        partial_variables={
            "format_instructions": PydanticOutputParser(pydantic_object=ReviewerOutput).get_format_instructions()
        }
    )
    