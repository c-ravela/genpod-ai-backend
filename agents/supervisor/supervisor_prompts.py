""" Contain all the prompts needed by the Supervisor Agent"""
from langchain.prompts import PromptTemplate

class SupervisorPrompts():
    delegator_prompt = PromptTemplate(
        template="""You are a Supervisor of a team who always tracks the status of the project and the tasks \n 
        Active team members are: \n\n {team_members} \n\n
        What do each team memeber do:\n
        Architect: ['Creates Requirements document','Creates Deliverables','Answer any additional information']
        RAG: Contains proprietary information so must be called when such information is needed

        If the document contains keywords related to the user question, grade it as relevant. \n
        It does not need to be a stringent test. The goal is to filter out erroneous retrievals. \n
        Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question. \n
        Provide the binary score as a JSON with a single key 'score' and no premable or explanation.""",
        input_variables=["question", "document"],
    )
    
    response_evaluator_prompt = PromptTemplate(
        template="""You are a Supervisor responsible for evaluating the completeness of responses from team members. Your task is to determine if a given response requires additional information or clarification.

        Current team members: {team_members}

        Response to evaluate: {response}

        Original user query: {user_query}

        Evaluation criteria:
        1. Does the response fully address the user's query?
        2. Is the information provided clear and comprehensive?
        3. Are there any obvious gaps or missing details in the response?
        4. Would the user likely need to ask follow-up questions based on this response?

        Provide a binary assessment as a JSON with a single key 'needs_additional_info'. Use 'true' if the response requires more information, and 'false' if it's complete and satisfactory. Do not include any explanation or preamble in your output.

        Example output:
        {"needs_additional_info": true}
        or
        {"needs_additional_info": false}""",
        input_variables=["team_members", "response", "user_query"],
    )

    architect_call_prompt = PromptTemplate(
        template="""Given the user prompt and the additional information build a complete requirements document for the project and split the deliverables into task.
            Do not assume anything and request for additional information if provided information is not sufficient to complete the task or something is missing."""
        )

    additional_info_req_prompt = PromptTemplate(
        template="""A fellow agent is stuck with something and is requesting additional info on the question"""
    )
