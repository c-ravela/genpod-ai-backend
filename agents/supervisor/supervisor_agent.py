import ast
import json
from typing import TYPE_CHECKING, Dict, List, Tuple

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from agents.agent.agent import Agent
from agents.supervisor.supervisor_state import SupervisorState
from configs.project_config import ProjectAgents
from configs.supervisor_config import calling_map
from models.constants import ChatRoles, PStatus, Status
from models.models import RequirementsDocument, Task
from models.supervisor import QueryList
from prompts.supervisor import SupervisorPrompts
from utils.fuzzy_rag_cache import FuzzyRAGCache
from utils.logs.logging_utils import logger

# to avoid circular dependency
if TYPE_CHECKING:
    from genpod.team import TeamMembers  # Adjust import path as needed

class SupervisorAgent(Agent[SupervisorState, SupervisorPrompts]):

    team: 'TeamMembers'

    def __init__(self, llm: ChatOpenAI) -> None:

        super().__init__(
            ProjectAgents.supervisor.agent_id,
            ProjectAgents.supervisor.agent_name,
            SupervisorState(),
            SupervisorPrompts(),
            llm
        )
        self.team = None

        self.rag_cache = FuzzyRAGCache()
        self.rag_cache_building = ''

        # TODO: NEED to check when this field has to be updated back and forth
        self.is_test_generator_agent_called: bool = False

        self.is_rag_cache_created: bool = False # Represents whether rag cache was created or not. single time update
        self.is_initial_additional_info_ready: bool = False # single time update. set once 
        self.are_requirements_prepared: bool = False # single time update

        self.calling_agent: str = ""
        self.called_agent: str = ""

        self.responses: Dict[str, List[Tuple[str, Task]]] = {}
        self.tasks = []
   
        # prompts
        self.project_init_questionaire = self.prompts.init_rag_questionaire_prompt | self.llm
        self.evaluation_chain = self.prompts.follow_up_questions | self.llm

    def setup_team(self, team: 'TeamMembers') -> None:
        """
        """

        self.team = team

    def build_rag_cache(self, query: str) -> tuple[list[str], str]:
        """
        takes the user requirements as an input and prepares a set of queries(anticipates the questions) 
        that team members might get back with and prepares the answers for them and hold them in the 
        rag cache.

        returns list of queries and response to the queries.
        """
        # I need to build a rag_cache during kick_off with answers to questions about requirements.
        context = ''
        count = 3

        # Prepare questionaire for rag cache
        while(count > 0):
            try:
                req_queries = self.project_init_questionaire.invoke({'user_prompt': query,'context':context})
                req_queries = ast.literal_eval(req_queries.content)
                validated_requirements_queries = QueryList(req_queries=req_queries)
                break
            except (ValidationError, ValueError, SyntaxError) as e:
                context += str(e)
                count = count-1

        if validated_requirements_queries.req_queries:
            final_response = ''

            for req_query in validated_requirements_queries.req_queries:
                result = self.rag_cache.get(req_query)

                if result is not None:
                    logger.debug("Cache hit for query: %s", req_query)
                    rag_response = result
                else:
                    logger.debug("Cache miss for query: %s", req_query)
                    logger.info(f'----------{self.team.rag.member_name} Agent Called to Query----------')
                    logger.info("Query: %s", req_query)
                    
                    result = self.team.rag.invoke({
                        'question': req_query, 
                        'max_hallucination': 3
                    })

                    rag_response = result['generation']
                    self.rag_cache.add(req_query, rag_response)
                    
                    logger.info(f"'----------{self.team.rag.member_name} Agent Response----------")
                    logger.info(f"{self.team.rag.member_name} Response: %s", rag_response)

                    if result['query_answered'] is True:
                        # Evaluate the RAG response
                        evaluation_result = self.evaluation_chain.invoke({
                            'user_query':req_query,
                            'initial_rag_response':rag_response}
                        )
                        
                        if evaluation_result.content.startswith("COMPLETE"):
                            final_response += f"Question: {req_query}\nAnswer: {rag_response}\n\n"
                        elif evaluation_result.content.startswith("INCOMPLETE"):
                            follow_up_query = evaluation_result.content.split("Follow-up Query:")[1].strip()
                            
                            logger.info("----------Follow-up query needed----------")
                            logger.info("Follow-up: %s", follow_up_query)
                            
                            # Ask the follow-up query to the RAG agent
                            follow_up_result = self.team.rag.invoke({
                                'question': follow_up_query, 
                                'max_hallucination': 3
                            })

                            follow_up_response = follow_up_result['generation']
                            self.rag_cache.add(follow_up_query, follow_up_response)
                            
                            final_response += f"Question: {req_query}\nInitial Answer: {rag_response}\nFollow-up Question: {follow_up_query}\nFollow-up Answer: {follow_up_response}\n\n"
                        else:
                            logger.info("Unexpected evaluation result format")

                            final_response += f"Question: {req_query}\nAnswer: {rag_response}\n\n"

            return (validated_requirements_queries.req_queries, final_response)
        else:
            return ([], 'Failed to initialize project')

    def instantiate_state(self, state: SupervisorState) -> SupervisorState:
        """"""
        if self.team is None:
            raise ValueError(
                f"Error: The team for '{self.agent_name}' has not been initialized. "
                f"Current value of 'self.team': {self.team}. "
                "Please ensure that the 'set_team' method has been called on the supervisor agent "
                "to initialize the team before attempting this operation."
            )

        # initialize supervisor state
        state['project_name'] = ""
        
        state['project_status'] = PStatus.RECEIVED

        state['microservice_name'] = ""

        state['tasks'] = []
        state['current_task'] = Task()

        state['requirements_document'] = RequirementsDocument()

        state['messages'] += [
            (
                ChatRoles.SYSTEM.value, 
                f'A new project with the following details has been received from the user: {state["original_user_input"]}'
            )
        ]
        state['human_feedback'] = []

        state['rag_cache_queries'] = []
        
        state['is_rag_query_answered'] = False
        state['rag_retrieval'] = ''
        state['agents_status'] = ''

        state['planned_tasks'] = []
        state['planned_task_map'] = {}
        state['planned_task_requirements'] = {}
        state['project_folder_strucutre'] = ''
        state['code'] = ''
        state['files_created'] = []
        state['infile_license_comments'] = {}
        state['commands_to_execute'] = {}

        self.responses = {member.member_id: [] for member in self.team.get_team_members_as_list()}
        
        logger.info("Supervisor state has been initialized successfully.")

        return state

    def call_rag(self, state: SupervisorState) -> SupervisorState:
        """
        """
        logger.info(f"{self.team.rag.member_name} has called!")

        # check if rag cache was ready if not prepare one
        if not self.is_rag_cache_created:
            logger.info(f"{self.team.rag.member_name}: creating the RAG cache.")
            
            # TODO - MEDIUM: Define a proper data structure for holding the RAG queries and answers together.
            # Reason: self.rag_cache_building is a string that holds all the queries and answers.
            # When a cache hit occurs, we use self.rag_cache_building as a response. This can provide too much 
            # information, which might be unnecessary at that moment or might include irrelevant information.
            # SIDE EFFECTS: 
            # 1. LLMs might hallucinate.
            # 2. Increases the usage of prompt tokens.

            # TODO - MEDIUM: Set a cache size limit.
            # Potential issue: As the cache grows, performance issues may arise, significantly slowing down the 
            # application since we are dealing with strings and performing many string comparisons.
            # Solution: Choose and implement algorithms like LRU (Least Recently Used) or LFU (Least Frequently Used).
            # state['rag_cache_queries'], self.rag_cache_building = self.build_rag_cache(state['original_user_input'])
            self.is_rag_cache_created = True
            logger.info(f"{self.team.rag.member_name}: The RAG cache has been created. The following queries were used during the process: {state['rag_cache_queries']}")

        question = state['current_task'].question
        try:
            if state['project_status'] == PStatus.RECEIVED:
                logger.info(f"{self.team.rag.member_name}: Received user requirements and gathering additional information.")
                state['messages'] += [
                    (
                        ChatRoles.AI.value,
                        f"{self.team.rag.member_name}: Received user requirements and gathering additional information."
                    )
                ]
            else:
                logger.info(f"{self.team.rag.member_name}: Received a query from team members and preparing an answer.")
                state['messages'] += [
                    (
                        ChatRoles.AI.value,
                        f"{self.team.rag.member_name}: Received a query from team members and preparing an answer."
                    )
                ]
            
            # Check RAG cache for the information first
            result = self.rag_cache.get(question)
            if result is not None:
                logger.debug("Cache hit for query: \n%s",question)

                state['is_rag_query_answered'] = True
            else:
                logger.debug("Cache miss for query: \n%s", question)

                additional_info = self.team.rag.invoke({
                    'question': question,
                    'max_hallucination': 3
                })

                result = additional_info['generation']
                state['is_rag_query_answered'] = additional_info['query_answered']
                self.rag_cache.add(question, result)
            
            logger.info(f"{self.team.rag.member_name} is ready with a response for the query: {question}")
        except Exception as e:
            raise(e)
        
        # TODO - LOW: Perform conditional checks with project status and current task status (if needed).
        # Relying solely on current_task to make decisions is causing significant confusion.
        # This will help with project maintenance and readability.
        if state['current_task'].task_status == Status.NEW:
            state['current_task'].additional_info = result + "\n" + self.rag_cache_building
            state['current_task'].task_status = Status.DONE
            self.is_initial_additional_info_ready = True
            state['rag_retrieval'] = result + "\n" + self.rag_cache_building
            state['agents_status'] = f'{self.team.rag.member_name} completed'
            self.called_agent = self.team.rag.member_id
            self.responses[self.team.rag.member_id].append(("Returned from RAG database", state['current_task']))
            
            return {**state}
        elif state['current_task'].task_status == Status.AWAITING:
            #  This mean the query RAG Agent to get additional information for another agent which will be present 
            # in called agent and that will and should never be updated when returning

            # TODO - MEDIUM: We are adding strings like `RAG_Response:` and using this word for conditional checks in a few places.
            # problem is performance degradation: the application slows down because we are searching for a small string in a very large 
            # string.
            state['current_task'].task_status = Status.RESPONDED
            state['current_task'].additional_info += "\nRAG_Response:\n" + result
            state['rag_retrieval'] += result
            state['agents_status'] = f'{self.team.rag.member_name} completed'
            self.called_agent = self.team.rag.member_id
            self.responses[self.team.rag.member_id].append(("Returned from RAG database serving a query", state['current_task']))
            
            return {**state}
        
        return {**state}
            
    def call_architect(self, state: SupervisorState) -> SupervisorState:
        """"""
        
        if state['project_status'] == PStatus.INITIAL:
            logger.info(f"{self.team.architect.member_name}: Started  working on requirements document.")

            architect_result = self.team.architect.invoke({
                'current_task': state['current_task'],
                'project_status': state['project_status'],
                'original_user_input': state['original_user_input'],
                'project_path': state['project_path'],
                'user_requested_standards': state['current_task'].additional_info,
                'license_text': state['license_text'],
                'messages': []
            })

            # if the task_status is done that mean architect has generated all the required information for team
            if architect_result['current_task'].task_status == Status.DONE:
                self.are_requirements_prepared = True
                state['current_task'] = architect_result['current_task']
                state['agents_status'] = f'{self.team.architect.member_name} completed'
                self.responses[self.team.architect.member_id].append(("Returned from Architect", architect_result['tasks']))
                state['tasks'] = architect_result['tasks']
                state['requirements_document'] = architect_result['requirements_document']
                state['project_name'] = architect_result['project_name']
                state['microservice_name'] = architect_result['project_name']
                state['project_folder_strucutre'] = architect_result['project_folder_structure']

                # Lets extract the coder_inputs from the architect's final state
                # TODO: We want to be able to ask each agent what they need as input to start working that way we don't need to hardcode it this way.
                coder_inputs_needed = ['project_path', 'license_text', 'license_url', 'project_name', 'project_folder_structure', 'requirements_document', 'current_task']
                state['coder_inputs'] = {}

                for needed_input in coder_inputs_needed:
                    if needed_input in architect_result.keys():
                        state['coder_inputs'][needed_input] = architect_result[needed_input]
                    else:
                        # Check in supervisor_state for user provided value, such as license_url
                        state['coder_inputs'][needed_input] = state[needed_input]

                self.called_agent = self.team.architect.member_id

                return state
            else:
                #  TODO: if task_status=='AWAITING', that means Current task could not be completed by architect call supervisor to deal with the same task
                # state['project_status'] = PStatus.MONITORING.value
                state['current_task'] = architect_result['current_task']
                state['agents_status'] = f'{self.team.architect.member_name} Awaiting'
                self.responses[self.team.architect.member_id].append(("Returned from Architect with a question:", architect_result['current_task'].question))
                self.called_agent = self.team.architect.member_id

                return {**state}
        elif state['project_status'] == PStatus.MONITORING:
            # Need to query Architect to get additional information for another agent which will be present in called agent and that will never be updated when returning
            logger.info("----------Querying Architect----------")

            architect_result = self.team.architect.invoke({
                'current_task': state['current_task'],
                'project_status': state['project_status'],
                'original_user_input': state['original_user_input'],
                'project_path': state['project_path'],
                'user_requested_standards': state['current_task'].additional_info,
                'messages': []
            })
            
            logger.info("----------Response from Architect Agent----------")
            logger.info("Architect Response: %r", architect_result['current_task'])

            if architect_result['query_answered'] is True:
                state['agents_status'] = f'{self.team.architect.member_name} completed'
                self.responses[self.team.architect.member_id].append(("Returned from Architect serving a Query", architect_result['current_task']))
                self.called_agent = self.team.architect.member_id
                state['current_task'] = architect_result['current_task']

                return {**state}
            elif state['is_rag_query_answered'] is False and architect_result['query_answered'] is False:
                # Additional Human input is needed
                state['current_task'] = architect_result['current_task']
                state['project_status'] = PStatus.HALTED
        
        return {**state}

    def call_coder(self, state: SupervisorState) -> SupervisorState:
        """
        """
        self.is_test_generator_agent_called=False

        state['messages'] += [(
            ChatRoles.AI.value,
            'Calling Architect Agent'
        )]

        logger.info("---------- Calling Coder ----------")
       
        coder_result = self.team.coder.invoke({
            **state['coder_inputs'],
            'messages':[]
        })

        if coder_result['current_task'].task_status.value == Status.DONE.value:
            logger.info("Coder completed work package")

            state['agents_status'] = f'{self.team.coder.member_name} Completed'
        elif coder_result['current_task'].task_status.value == Status.ABANDONED.value:
            logger.info("Coder unable to complete the work package due to : %s", coder_result['current_task'].additional_info)

            state['agent_status'] = f"{self.team.coder.member_name} Completed With Abandonment"
        else:
            logger.info("Coder awaiting for additional information\nCoder Query: %s", coder_result['current_task'].question)

            state['agents_status'] = f'{self.team.coder.member_name} Awaiting'

        self.called_agent = self.team.coder.member_id
        self.responses[self.team.coder.member_id].append(("Returned from Coder", state['current_task']))

        return {**state}

    def call_test_code_generator(self, state: SupervisorState) -> SupervisorState:
        """
        """
        
        state['messages'] += [(
            ChatRoles.AI.value,
            'Calling Test Code Generator Agent'
        )]

        logger.info("---------- Calling Test Code Generator ----------")

        test_coder_result = self.team.tests_generator.invoke({
            **state['coder_inputs'],
            'messages': []
        })

        state['coder_inputs']['test_code'] = test_coder_result['test_code']
        state['coder_inputs']['functions_skeleton'] = test_coder_result['functions_skeleton']

        if test_coder_result['current_task'].task_status.value == Status.DONE.value:
            logger.info("Test Code Generator completed work package")
            state['agents_status'] = f'{self.team.tests_generator.member_id} Completed'
        elif test_coder_result['current_task'].task_status.value == Status.ABANDONED.value:
            logger.info("Test Coder Generator unable to complete the work package due to : %s", test_coder_result['current_task'].additional_info)
            state['agent_status'] = f'{self.team.tests_generator.member_id} Completed With Abandonment'
        else:
            logger.info("Test Coder Generator awaiting for additional information\nCoder Query: %s", test_coder_result['current_task'].question)
            state['agents_status'] = f'{self.team.tests_generator.member_id} Generator Awaiting'

        self.called_agent = self.team.tests_generator.member_id
        self.responses[self.team.tests_generator.member_id].append(("Returned from Test Coder Generator", state['current_task']))
        self.is_test_generator_agent_called=True

        return {**state}
    
    def call_supervisor(self, state: SupervisorState) -> SupervisorState:
        """
        """

        if state['project_status'] == PStatus.RECEIVED:
            state['messages'] += [
                (
                    ChatRoles.AI.value,
                   f"The Genpod team has started working on the project with ID: {state['project_id']} and the following microservice ID: {state['microservice_id']}."
                )
            ]

            # create a task for rag agent
            state['current_task'] = Task(
                description='retrieve additional context from RAG system',
                task_status = Status.NEW,
                additional_info = '',
                question=state['original_user_input']
            )
            state['project_status'] = PStatus.NEW

            return state
        elif state['project_status'] == PStatus.NEW:
            
            # If the task is marked as done, it means the RAG agent has gathered the additional information 
            # needed for the team to begin the project.
            if state['current_task'].task_status == Status.DONE:
                if self.is_initial_additional_info_ready:
                    state['project_status'] = PStatus.INITIAL
                
                    # create a new task for the architect
                    state['current_task'] = Task(
                        description=self.prompts.architect_call_prompt.format(),
                        task_status=Status.NEW,
                        additional_info=state['rag_retrieval'],
                        question=''
                    )            
            self.calling_agent = self.team.supervisor.member_id
            
            return state
        elif state['project_status'] == PStatus.INITIAL:

            # Architect has prepared all the required information.
            if state['current_task'].task_status == Status.DONE:
                exit(0)
                state['project_status'] = PStatus.EXECUTING
            elif state['current_task'].task_status == Status.AWAITING:
                # Architect need additional information to complete the assigned task. architect provides query in the task packet 
                # use it to query RAG.
                state['project_status'] = PStatus.MONITORING
        
            return state
        elif state['current_task'].task_status == PStatus.MONITORING:
            # TODO: update this conditional logic based current task status == RESPONDED
            if "RAG_Response" in state['current_task'].additional_info and "Architect_Response" in state['current_task'].additional_info:
                state['project_status'] = PStatus.EXECUTING
            
            return state
        elif state['project_status'] == PStatus.EXECUTING and state['current_task'].task_status==Status.AWAITING:
            state['project_status'] = PStatus.MONITORING
            self.calling_agent = self.called_agent

            return {**state}
        elif state['project_status'] == PStatus.EXECUTING.value and (state['current_task'].task_status.value == Status.DONE.value or state['current_task'].task_status.value == Status.INPROGRESS.value):
            if state['current_task'].task_status.value == Status.INPROGRESS.value:
                # We need to work on calling coder on planned tasks
                # We will be calling coder, so we need to pick tasks from the planned task now and add it to coder_inputs item of the state
                if len(state['planned_tasks']) > 0:
                    state['coder_inputs']['current_task'] = state['planned_tasks'].pop(0)
                    # we can return here because we have a work_package to call the coder with
                    self.calling_agent = self.team.supervisor.member_id

                    return {**state}
                else:
                    # all work_packages are provided to coder so we can now move to next deliverable
                    state['current_task'].task_status = Status.DONE

            if state['current_task'].task_status.value == Status.DONE.value:
                # We need to work on calling planner on deliverables provided by architect
                if len(state['tasks']) is None or len(state['tasks']) == 0:
                    new_task = None
                else:
                    new_task = state['tasks'].pop(0)
                
                if new_task is None:
                    logger.info("Received next task as None. Changing to Halted State.")

                    state['project_status'] = PStatus.HALTED.value
                else:
                    state['current_task'] = new_task

                    requirements_doc = state['requirements_document'].to_markdown()
                    state['current_task'].additional_info = requirements_doc + '\n' + state['rag_retrieval']
                    
                self.called_agent = self.team.supervisor.member_id

                return {**state}
        elif state['project_status'] == PStatus.HALTED:
            # TODO: Figure out when this stage occurs and handle the logic
            return state
        elif state['project_status'] == PStatus.DONE:
            # TODO: Figure out when this stage occurs and handle the logic
            return state
        else:
            return state
        
    def call_planner(self, state: SupervisorState) -> SupervisorState:
        """
        """
        
        logger.info("----------Calling Planner----------")
        planner_result = self.team.planner.invoke({
            'current_task': state['current_task'],
            'project_path': state['project_path']
        })
        
        state['current_task'] = planner_result['response'][-1]
        if state['current_task'].task_status == Status.DONE:
            logger.info("----------Response from Planner Agent----------")
            logger.info("Planner Response: %r",planner_result['planned_task_map'])

            state['agents_status'] = f'{self.team.planner.member_name} completed'
            self.called_agent = self.team.planner.member_id
            self.responses[self.team.planner.member_id].append(("Returned from Planner",state['current_task']))

            return {**state}
        elif state['current_task'].task_status == Status.INPROGRESS:
            state['planned_task_map'] = {**planner_result['planned_task_map']}
            state['planned_task_requirements'] = {**planner_result['planned_task_requirements']}
          
            # TODO: use the response packet and build the planned tasks list
            # Get the workpackages created by planner for the current task a.k.a. deliverable
          
            for value in state['planned_task_map'][state['current_task'].description]:
                # for each workpackage we need to create a planned_task
                if state['planned_tasks'] is None:
                    state['planned_tasks'] = [Task(description=json.dumps({"work_package_name": value, **state['planned_task_requirements'][value]}), task_status=Status.NEW.value, additional_info='',question='')]
                else:
                    state['planned_tasks'].append(Task(description=json.dumps({"work_package_name": value, **state['planned_task_requirements'][value]}), task_status=Status.NEW.value, additional_info='',question=''))
           
            state['agent_status'] = f"{self.team.planner.member_name} built the work packages"
            self.called_agent = self.team.planner.member_id
            self.responses[self.team.planner.member_id].append(("Returned from Planner",state['current_task']))

            logger.info("----------Response from Planner Agent----------")
            logger.info("Planner Response: %r",planner_result['planned_task_map'])

            return {**state}
        else:
            logger.info("----------Response from Planner Agent----------")
            logger.info("Planner Response: %s", state['current_task'].question)

            state['agents_status'] = f'{self.team.planner.member_name} Awaiting'
            self.called_agent = self.team.planner.member_id
            self.responses[self.team.planner.member_id].append(("Returned from Planner with a question", state['current_task'].question))

            return {**state}

    def call_human(self, state: SupervisorState) -> SupervisorState:
        # Display relevant information to the human
        # pprint(f"----------Supervisor current state----------\n{state}")
        # Prompt for input
        if state['current_task'].question != '':
            # Display the current task being performed to the user
            logger.info("----------Current Task that needs your assistance to proceed----------")
            logger.info("Current Task: %r", state['current_task'])
            # Get human input
            human_input = input(f"Please provide additional input for the question:\n{state['current_task'].question}")

            # Append the human input to current_task additional_info
            state['current_task'].additional_info += '\nHuman_Response:\n' + human_input

            # Update the project status back to executing
            state['project_status'] = PStatus.EXECUTING.value

            # Add the human responses to the rag cache for future queries and maintain a copy in state too
            human_feedback = (state['current_task'].question, f'Response from Human: {human_input}')
            state['human_feedback'] += [human_feedback]
            self.rag_cache.add(state['current_task'].question, human_input)

        else:
            logger.info("----------Unable to handle Human Feedback currently so ending execution----------")
            
        human_input = input(f"Please provide additional input for the question:\n{state['current_task'].question}")

        # Process the input and update the state
        state['human_feedback'] += [human_input]
        state['project_status'] = PStatus.EXECUTING.value
        # state.human_feedback = human_input

        return {**state}

    def pick_next_task(self, state: SupervisorState) -> Task:
        if len(state['tasks']) is None:
            return None
        else:
            next_task = state['tasks'].pop(0)

            return next_task

    # TODO: fix this function conditions. Its too complex for the new users to understand whats happening
    def delegator(self, state: SupervisorState) -> str:
        """
        """

        if state['project_status'] == PStatus.NEW:
            # Project has been received by the team.
            # RAG(team member) now need to gather additonal information for the project
            # additional information? yep a more detailed information about the project.
            # user input would be to vague to start working on the project and results in a
            # more generic output. so we need to more specific on what user is expecting.
            # RAG holds the some standards documents and it fetches the relevant information related
            # to the project to help team members efficient and qualified output.

            return 'call_rag'
        elif state['project_status'] == PStatus.INITIAL:
            # Once the project is ready with additional information needed. Team can starting working on the project
            # architect is first team member who receives the project details and prepares the the requirements out of it.
            # In this process if architect need aditional information thats when RAG comes into play at this phase of Project.
            if self.is_initial_additional_info_ready:
                return 'call_architect'
            else:
                return 'call_rag'
        elif state['project_status'] == PStatus.MONITORING:
            if state['current_task'].task_status == Status.AWAITING:
                return 'call_rag'
            elif state['current_task'].task_status == Status.RESPONDED:
                # TODO - LOW: Make this block logic dynamic
                # Current there is only one agent which asks question
                # but in future there might more agents which might request
                # for additional information.
                # Make this case statements dynamic. so that whoever has the requested the
                # additional information, flow goes back to them.
                return 'call_architect'
        elif state['project_status']==PStatus.EXECUTING and self.calling_agent!=self.team.supervisor.member_id:
            return calling_map[self.calling_agent]
        elif state['project_status']==PStatus.EXECUTING and (self.called_agent==self.team.architect.member_id or self.called_agent==self.team.supervisor.member_id):
            return 'call_planner'
        elif state['project_status']==PStatus.EXECUTING and (self.called_agent==self.team.planner.member_id or self.called_agent==self.team.coder.member_id) and ((classifier := json.loads(state['coder_inputs']['current_task'].description))['is_function_generation_required']) and not(self.is_test_generator_agent_called) :
            return 'call_test_code_generator' 
        elif state['project_status']==PStatus.EXECUTING and (self.called_agent==self.team.planner.member_id or self.called_agent==self.team.coder.member_id or self.called_agent =='TestGenerator') and (((classifier := json.loads(state['coder_inputs']['current_task'].description))['is_function_generation_required'] and self.is_test_generator_agent_called) or not ((classifier := json.loads(state['coder_inputs']['current_task'].description))['is_function_generation_required'])) :
            return 'call_coder'
        elif state['project_status']==PStatus.HALTED:
            return 'update_state' #'Human'

        return "update_state"
