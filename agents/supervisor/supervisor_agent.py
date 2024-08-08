import ast
import json
from typing import Dict, List, Any, Tuple, Union

from pydantic import ValidationError
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama

from agents.agent.agent import Agent
from agents.agent.graph import Graph

from agents.coder.graph import CoderGraph
from agents.architect.graph import ArchitectGraph
from agents.rag_workflow.rag_graph import RAGWorkFlow
from agents.planner.planner_graph import PlannerWorkFlow

from agents.supervisor.supervisor_models import QueryList
from agents.supervisor.supervisor_prompts import SupervisorPrompts
from agents.supervisor.supervisor_state import SupervisorState

from configs.project_config import AgentConfig
from configs.project_config import ProjectAgents
from configs.supervisor_config import calling_map

from models.constants import PStatus, Status
from models.models import Task

from utils.fuzzy_rag_cache import FuzzyRAGCache
from utils.logs.logging_utils import logger

class SupervisorAgent(Agent[SupervisorState, SupervisorPrompts]):
    def __init__(self, 
                llm: Union[ChatOpenAI, ChatOllama], 
                collections: dict[str, str], 
                user_input: str, rag_try_limit: int, 
                project_path: str, persistance_db_path: str,
                agents_config: Dict[str, AgentConfig]):

        super().__init__(
            ProjectAgents.supervisor.agent_name,
            ProjectAgents.supervisor.agent_id,
            SupervisorState(),
            SupervisorPrompts(),
            llm
        )

        self.agents_config = agents_config
        self.collections = collections

        self.rag_try_limit = rag_try_limit
        self.project_path = project_path
        self.persistance_db_path = persistance_db_path

        self.rag_cache = FuzzyRAGCache()
        self.rag_cache_building = ''

        self.calling_agent = None
        self.called_agent = None
        self.team_members: Dict[str, Graph] = {k: None for k, v in self.agents_config.items()}
        # {
        #     'Architect': None,
        #     'RAG': None,
        #     'Coder': None,
        #     'Planner': None
        # }

        self.user_prompt = user_input
        self.responses: Dict[str, List[Tuple[str, Task]]] = {k: [] for k, v in self.agents_config.items()}
        self.tasks = []
   
        self.project_status: str = None
        self.project_init_questionaire = self.prompts.init_rag_questionaire_prompt | self.llm
        self.evaluation_chain = self.prompts.follow_up_questions | self.llm

    def build_rag_cache(self, query: str):
        # I need to build a rag_cache during kick_off with answers to questions about requirements.
        context = ''
        count = 3
        while(count>0):
            try:
                req_queries = self.project_init_questionaire.invoke({'user_prompt':query,'context':context})
                req_queries = ast.literal_eval(req_queries.content)
                validated_requirements_queries = QueryList(req_queries=req_queries)
                break
            except (ValidationError, ValueError, SyntaxError) as e:
                context += str(e)
                count = count-1
        # if len(validated_requirements_queries.req_queries) is not None:
        #     final_response = ''
        #     for req_query in validated_requirements_queries.req_queries:
        #         result = self.rag_cache.get(req_query)
        #         if result is not None:
        #             print(f"Cache hit for query, will not response to: {req_query}")
        #         else:
        #             print(f"Cache miss for query: {req_query}")
        #             print(f'----------RAG Agent Called to Query----------\n{req_query}')
        #             result = self.team_members[ProjectAgents.rag.agent_id].workflow.invoke({'question': req_query,'iteration_count':self.rag_try_limit}, {'configurable':{'thread_id':self.memberids['RAG']}})
        #             self.rag_cache.add(req_query, result['generation'])
        #             print(f'----------RAG Agent Response----------\n{result['generation']}')
        #             if result['query_answered'] is True:
        #                 final_response += f"Question: {req_query}\nAnswer: {result['generation']}"
        #     return final_response
        if validated_requirements_queries.req_queries:
            final_response = ''
            for req_query in validated_requirements_queries.req_queries:
                result = self.rag_cache.get(req_query)
                if result is not None:
                    # print(f"Cache hit for query: {req_query}")
                    logger.debug("Cache hit for query: %s", req_query)
                    rag_response = result
                else:
                    # print(f"Cache miss for query: {req_query}")
                    logger.debug("Cache miss for query: %s", req_query)
                    # print(f'----------RAG Agent Called to Query----------\n{req_query}')
                    logger.info(f'----------{ProjectAgents.rag.agent_name} Agent Called to Query----------')
                    logger.info("Query: %s", req_query)
                    result = self.team_members[ProjectAgents.rag.agent_id].workflow.invoke(
                        {  
                            'question': req_query, 
                            'iteration_count': self.rag_try_limit, 
                            'max_hallucination': 3
                        }, 
                        {
                            'configurable': {
                                'thread_id': self.agents_config[ProjectAgents.rag.agent_id].thread_id
                            }
                        }
                    )
                    rag_response = result['generation']
                    self.rag_cache.add(req_query, rag_response)
                    # print(f'----------RAG Agent Response----------\n{rag_response}')
                    logger.info(f"'----------{ProjectAgents.rag.agent_name} Agent Response----------")
                    logger.info(f"{ProjectAgents.rag.agent_name} Response: %s", rag_response)
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
                            # print(f"\n----------Follow-up query needed----------\n{follow_up_query}")
                            logger.info("----------Follow-up query needed----------")
                            logger.info("Follow-up: %s", follow_up_query)
                            
                            # Ask the follow-up query to the RAG agent
                            follow_up_result = self.team_members[ProjectAgents.rag.agent_id].workflow.invoke(
                                {
                                    'question': follow_up_query, 
                                    'iteration_count': self.rag_try_limit, 
                                    'max_hallucination': 3
                                }, 
                                {
                                    'configurable': {
                                        'thread_id': self.agents_config[ProjectAgents.rag.agent_id].thread_id
                                    }
                                }
                            )
                            follow_up_response = follow_up_result['generation']
                            self.rag_cache.add(follow_up_query, follow_up_response)
                            
                            final_response += f"Question: {req_query}\nInitial Answer: {rag_response}\nFollow-up Question: {follow_up_query}\nFollow-up Answer: {follow_up_response}\n\n"
                        else:
                            # print("Unexpected evaluation result format.")
                            logger.info("Unexpected evaluation result format")
                            final_response += f"Question: {req_query}\nAnswer: {rag_response}\n\n"
            return final_response
        else:
            return 'Failed to initialize project'

    def instantiate_team_members(self, state: SupervisorState):
        for member,_ in self.team_members.items():
            if member==ProjectAgents.architect.agent_id:
                self.team_members[member] = ArchitectGraph(
                    self.agents_config[member].llm,
                    self.persistance_db_path
                )

            elif member==ProjectAgents.rag.agent_id:
                # We can to implement a scenario where we are able to use appropriate collection_name from the list of collections based on the user_input
                # This will probably mechanism should probably go inside ragworkflow implementation. For now lets keep it simple
                self.team_members[member] = RAGWorkFlow(
                    self.agents_config[member].llm,
                    collection_name=list(self.collections.keys())[0],
                    persistance_db_path=self.persistance_db_path,
                    persist_directory=self.collections[list(self.collections.keys())[0]]
                )

            elif member==ProjectAgents.planner.agent_id:
                self.team_members[member] = PlannerWorkFlow(
                    self.agents_config[member].llm,
                    self.persistance_db_path
                )

            elif member==ProjectAgents.coder.agent_id:
                self.team_members[member] = CoderGraph(
                    self.agents_config[member].llm,
                    self.persistance_db_path
                )

            elif member==ProjectAgents.tester.agent_id:
                raise NotImplementedError("Need implement flow for tester")
            
            elif member==ProjectAgents.modernizer.agent_id:
                raise NotImplementedError("Need implement flow for modernizer")

            else:
                continue

        # state['team_members'] = {**self.team_members}
        state['original_user_input'] = self.user_prompt
        state['project_path'] = self.project_path
        state['rag_retrieval'] = ''
        state['current_task'] = Task(description='retrieve additional context from RAG system',
                                     task_status = Status.NEW,
                                     additional_info = '',
                                     question=self.user_prompt)
        # state['agents_status'] = 'New'
        message = ('user','Start new Project')

        state['messages'] += [message]
        self.project_status = PStatus.NEW.value
        self.rag_cache_building = self.build_rag_cache(state['original_user_input'])
        logger.info("----All information gathered during project initiation phase----")
        logger.info("RAG Collection: %s",self.rag_cache_building)
        return {**state}

    def call_rag(self, state: SupervisorState) -> SupervisorState:
        rag_agent_config = self.agents_config[ProjectAgents.rag.agent_id]
        question = state['current_task'].question
        try:
            message = ('Assistant', f'Calling {rag_agent_config.agent_name} Agent')
            state['messages'] += [message]
            # print("----------Getting Additional information from RAG Agent----------")
            logger.info(f"----------Getting Additional information from {rag_agent_config.agent_name} Agent----------")
            # Check in cache first
            result = self.rag_cache.get(question)
            if result is not None:
                # print(f"Cache hit for query: \n{question}")
                logger.debug("Cache hit for query: \n%s",question)
                message = ('Assistant', f'Response from {rag_agent_config.agent_name}: {result}')
                state['rag_query_answer'] = True
                # return result
            else:
                # print(f"Cache miss for query: \n{question}")
                logger.debug("Cache miss for query: \n%s", question)
                # result = your_rag_query_function(query)  # Replace with your actual RAG query function
            # return result
                additional_info = self.team_members[rag_agent_config.agent_id].workflow.invoke(
                    {
                        'question': question,
                        'iteration_count': self.rag_try_limit, 
                        'max_hallucination': 3
                    }, 
                    {
                        'configurable': {
                            'thread_id': rag_agent_config.thread_id
                        }
                    }
                )
                result = additional_info['generation']
                state['rag_query_answer'] = additional_info['query_answered']
                self.rag_cache.add(question, result)
                message = ('Assistant', f'Response from {rag_agent_config.agent_name}: {result}')
            state['messages'] += [message]
            # print(f"----------Response from RAG Agent----------\n{result}")
            logger.info(f"----------Response from {rag_agent_config.agent_name} Agent----------")
            logger.info(f"{rag_agent_config.agent_name} Response: %s", result)
        except Exception as e:
            raise(e)
        if state['current_task'].task_status.value == Status.NEW.value:
            state['current_task'].additional_info = result + "\n" + self.rag_cache_building
            state['current_task'].task_status = Status.DONE
            state['rag_retrieval'] = result + "\n" + self.rag_cache_building
            state['agents_status'] = f'{rag_agent_config.agent_name} completed'
            self.called_agent = rag_agent_config.agent_id
            self.responses[rag_agent_config.agent_id].append(("Returned from RAG database", state['current_task']))
            return {**state}

        elif state['current_task'].task_status.value == Status.AWAITING.value:
            #  This mean the query RAG Agent to get additional information for another agent which wikk be present in called agent and that will and should never be updated when returning
            # if additional_info['generation'] != "I don't have any additional information about the question.":
            state['current_task'].additional_info += "\nRAG_Response:\n" + result
            state['rag_retrieval'] += result
            state['agents_status'] = f'{rag_agent_config.agent_name} completed'
            self.called_agent = rag_agent_config.agent_id
            self.responses[rag_agent_config.agent_id].append(("Returned from RAG database serving a query", state['current_task']))
            # state['rag_query_answer'] = additional_info['query_answered']
            return {**state}
        
        return {**state}
            
    def call_architect(self, state: SupervisorState) -> SupervisorState:
        architect_agent_config = self.agents_config[ProjectAgents.architect.agent_id]

        # Implement the logic to call the Architect agent
        if self.project_status == PStatus.INITIAL.value:
            message = ('Assistant', 'Calling Architect Agent')
            state['messages'] += [message]
            # print("----------Calling Architect----------")
            logger.info("----------Calling Architect----------")
            architect_result = self.team_members[architect_agent_config.agent_id].workflow.invoke(
                {
                    'current_task':state['current_task'],
                    'project_status':self.project_status,
                    'user_request': state['original_user_input'],
                    'generated_project_path':state['project_path'],
                    'user_requested_standards':state['current_task'].additional_info,
                    'license_text':state['license_text'],
                    'messages':[]
                },
                {
                    'configurable':{
                        'thread_id': architect_agent_config.thread_id
                    }
                }
            )

            # architect_state = self.team_members[architect_agent_config.agent_id].get_current_state()
            message = ('Assistant', f'Response from Architect: {architect_result['tasks']}')
            state['messages'] += [message]
            # print(f"----------Response from Architect Agent----------\n{architect_result['tasks']}")
            logger.info("----------Response from Architect Agent----------")
            logger.info("Archtect Response: %r", architect_result['tasks'])
            # Temporary validation this needs to be done by architect. Remove it once architect has implemented this.
            # if len(architect_result['tasks']) is not None:
            #     architect_result['current_task'].task_status = Status.DONE
            if architect_result['current_task'].task_status.value == Status.DONE.value:
                self.project_status = PStatus.EXECUTING.value
                state['current_task'] = architect_result['current_task']
                state['agents_status'] = f'{architect_agent_config.agent_name} completed'
                self.responses[architect_agent_config.agent_id].append(("Returned from Architect", architect_result['tasks']))
                state['tasks'] = architect_result['tasks']
                state['requirements_doc'] = architect_result['requirements_overview']
                state['project_path'] = architect_result['generated_project_path']
                
                # Lets extract the coder_inputs from the architect's final state
                # TODO: We want to be able to ask each agent what they need as input to start working that way we don't need to hardcode it this way.
                coder_inputs_needed = ['generated_project_path', 'license_text', 'license_url', 'project_name', 'project_folder_structure', 'requirements_overview']
                state['coder_inputs'] = {}
                for needed_input in coder_inputs_needed:
                    if needed_input in architect_result.keys():
                        state['coder_inputs'][needed_input] = architect_result[needed_input]
                    else:
                        # Check in supervisor_state for user provided value, such as license_url
                        state['coder_inputs'][needed_input] = state[needed_input]

                self.called_agent = architect_agent_config.agent_id

                return {**state}
            else:
                #  TODO: if task_status=='AWAITING', that means Current task could not be completed by architect call supervisor to deal with the same task
                # self.project_status = PStatus.MONITORING.value
                state['current_task'] = architect_result['current_task']
                state['agents_status'] = f'{architect_agent_config.agent_name} Awaiting'
                self.responses[architect_agent_config.agent_id].append(("Returned from Architect with a question:", architect_result['current_task'].question))
                self.called_agent = architect_agent_config.agent_id
                return {**state}
            
        elif self.project_status == PStatus.MONITORING.value:
            # Need to query Architect to get additional information for another agent which will be present in called agent and that will never be updated when returning
            # print("----------Querying Architect----------")
            logger.info("----------Querying Architect----------")
            architect_result = self.team_members[architect_agent_config.agent_id].workflow.invoke(
                {
                    'current_task':state['current_task'],
                    'project_status':self.project_status,
                    'user_request': state['original_user_input'],
                    'generated_project_path':state['project_path'],
                    'user_requested_standards':state['current_task'].additional_info,
                    'messages':[]
                },
                {
                    'configurable': {
                        'thread_id': architect_agent_config.thread_id
                    }
                }
            )
            # print(f"----------Response from Architect Agent----------\n{architect_result['current_task']}")
            logger.info("----------Response from Architect Agent----------")
            logger.info("Architect Response: %r", architect_result['current_task'])
            # architect_state = self.team_members[architect_agent_config.agent_id].get_current_state()
            if architect_result['query_answered'] is True:
                # self.project_status = PStatus.EXECUTING.value
                # state['current_task'].additional_info += "\nArchitect_Response:\n" + architect_state['current_task'].additional_info
                state['agents_status'] = f'{architect_agent_config.agent_name} completed'
                self.responses[architect_agent_config.agent_id].append(("Returned from Architect serving a Query", architect_result['current_task']))
                self.called_agent = architect_agent_config.agent_id
                state['current_task'] = architect_result['current_task']
                return {**state}
            elif state['rag_query_answer'] is False and architect_result['query_answered'] is False:
                # Additional Human input is needed
                state['current_task'] = architect_result['current_task']
                self.project_status = PStatus.HALTED.value
        
        return {**state}

    def call_coder(self, state: SupervisorState) -> SupervisorState:
        coder_agent_config = self.agents_config[ProjectAgents.coder.agent_id]
        # Implement the logic to call the Coder agent
        message = ('Assistant', 'Calling Architect Agent')
        state['messages'] += [message]
        logger.info("---------- Calling Coder ----------")
        coder_result = self.team_members[coder_agent_config.agent_id].workflow.invoke(
            {
                **state['coder_inputs'],
                'messages':[]
            },
            {
                'configurable': {
                    'thread_id': coder_agent_config.thread_id
                }
            }
        )
        # coder_state = self.team_members[coder_agent_config.agent_id].get_current_state()

        if coder_result['current_task'].task_status.value == Status.DONE.value:
            logger.info("Coder completed work package")
            state['agents_status'] = f'{coder_agent_config.agent_name} Completed'

        elif coder_result['current_task'].task_status.value == Status.ABANDONED.value:
            logger.info("Coder unable to complete the work package due to : %s", coder_result['current_task'].additional_info)
            state['agent_status'] = f"{coder_agent_config.agent_name} Completed With Abandonment"
        else:
            logger.info("Coder awaiting for additional information\nCoder Query: %s", coder_result['current_task'].question)
            state['agents_status'] = f'{coder_agent_config.agent_name} Awaiting'

        self.called_agent = coder_agent_config.agent_id
        self.responses[coder_agent_config.agent_id].append(("Returned from Coder", state['current_task']))
        return {**state}

    def call_supervisor(self, state: SupervisorState):
        supervisor_agent_config = self.agents_config[ProjectAgents.supervisor.agent_id]

        # Handling new requests vs pending requests
        if self.project_status == PStatus.NEW.value:
            if state['current_task'].task_status.value == Status.DONE.value:
                # Update the project status to initial
                self.project_status = PStatus.INITIAL.value
                # Create new task to be passed to architect
                _description = self.prompts.architect_call_prompt.format()
                _task_status = Status.NEW.value
                _additional_info = state['rag_retrieval']
                _question=''
                # Assign new task as the current task
                state['current_task'] = Task(description=_description,task_status=_task_status,additional_info=_additional_info,question=_question)            
            self.calling_agent = supervisor_agent_config.agent_id
            return {**state}
        elif self.project_status == PStatus.INITIAL.value:
            # If Architect has any queries during project Initial Stage which is common then we only want to call rag and send that response to architect
            if state['current_task'].task_status.value == Status.AWAITING.value and "RAG_Response" not in state['current_task'].additional_info:
                self.calling_agent = supervisor_agent_config.agent_id
            else:
                self.calling_agent = supervisor_agent_config.agent_id
            return {**state}
        elif self.project_status == PStatus.EXECUTING.value and state['current_task'].task_status.value==Status.AWAITING.value:
            self.project_status = PStatus.MONITORING.value
            self.calling_agent = self.called_agent
            return {**state}
        elif self.project_status == PStatus.MONITORING.value:
            if "RAG_Response" in state['current_task'].additional_info and "Architect_Response" in state['current_task'].additional_info:
                # state['current_task'].question = ''
                self.project_status = PStatus.EXECUTING.value
            # else:
            #     self.project_status = PStatus.HALTED.value
            return {**state}

        elif self.project_status == PStatus.EXECUTING.value and (state['current_task'].task_status.value == Status.DONE.value or state['current_task'].task_status.value == Status.INPROGRESS.value):
            # self.tasks = state['tasks']
            # new_task = None
            if state['current_task'].task_status.value == Status.INPROGRESS.value:
                # We need to work on calling coder on planned tasks
                # We will be calling coder, so we need to pick tasks from the planned task now and add it to coder_inputs item of the state
                if len(state['planned_tasks']) > 0:
                    state['coder_inputs']['current_task'] = state['planned_tasks'].pop(0)
                    # we can return here because we have a work_package to call the coder with
                    self.calling_agent = supervisor_agent_config.agent_id
                    return {**state}
                else:
                    # all work_packages are provided to coder so we can now move to next deliverable
                    state['current_task'].task_status = Status.DONE

            if state['current_task'].task_status.value == Status.DONE.value:
                # We need to work on calling planner on deliverables provided by architect
                if len(state['tasks']) is None or len(state['tasks']) == 0:
                    new_task = None
                else:
                    # next_task = Task(description=self.tasks.pop(), task_status=Status.NEW.value, additional_info='', question='')
                    new_task = state['tasks'].pop(0)
                # new_task = self.pick_next_task(state)
                if new_task is None:
                    logger.info("Received next task as None. Changing to Halted State.")
                    self.project_status = PStatus.HALTED.value
                else:
                    state['current_task'] = new_task
                    requirements_doc = ' '.join(str(value) for value in state['requirements_doc'].values())
                    state['current_task'].additional_info = requirements_doc + '\n' + state['rag_retrieval']
                    
                self.called_agent = supervisor_agent_config.agent_id
                return {**state}
        else:
            return {**state}

    def call_planner(self, state: SupervisorState):
        planner_agent_config = self.agents_config[ProjectAgents.planner.agent_id]
        # TODO: Implement Planner Agent
        # Implement the logic to call the Coder agent
        # response = self.team_members[planner_agent_config.agent_id].update_task(state['current_task'])
        # print("----------Calling Planner----------")
        logger.info("----------Calling Planner----------")
        planner_result = self.team_members[planner_agent_config.agent_id].workflow.invoke(
            {
                'current_task': state['current_task'],
                'generated_project_path': state['project_path']
            },
            {
                'configurable': {
                    'thread_id': planner_agent_config.thread_id
                }
            }
        )
        # planner_state = self.team_members[planner_agent_config.agent_id].get_current_state()
        state['current_task'] = planner_result['response'][-1]
        if state['current_task'].task_status.value == Status.DONE.value:
            # print(f"----------Response from Planner Agent----------\n{planner_result['deliverable_backlog_map']}")
            logger.info("----------Response from Planner Agent----------")
            logger.info("Planner Response: %r",planner_result['deliverable_backlog_map'])
            state['agents_status'] = f'{planner_agent_config.agent_name} completed'
            self.called_agent = planner_agent_config.agent_id
            self.responses[planner_agent_config.agent_id].append(("Returned from Planner",state['current_task']))
            return {**state}
        elif state['current_task'].task_status.value == Status.INPROGRESS.value:
            state['planned_task_map'] = {**planner_result['deliverable_backlog_map']}
            state['planned_task_requirements'] = {**planner_result['backlog_requirements']}
            # TODO: use the response packet and build the planned tasks list
            # Get the workpackages created by planner for the current task a.k.a. deliverable
            for value in state['planned_task_map'][state['current_task'].description]:
                # for each workpackage we need to create a planned_task
                if state['planned_tasks'] is None:
                    state['planned_tasks'] = [Task(description=json.dumps({"work_package_name": value, **state['planned_task_requirements'][value]}), task_status=Status.NEW.value, additional_info='',question='')]
                else:
                    state['planned_tasks'].append(Task(description=json.dumps({"work_package_name": value, **state['planned_task_requirements'][value]}), task_status=Status.NEW.value, additional_info='',question=''))
            state['agent_status'] = f"{planner_agent_config.agent_name} built the work packages"
            self.called_agent = planner_agent_config.agent_id
            logger.info("----------Response from Planner Agent----------")
            logger.info("Planner Response: %r",planner_result['deliverable_backlog_map'])
            self.responses[planner_agent_config.agent_id].append(("Returned from Planner",state['current_task']))
            return {**state}
        else:
            # print(f"----------Response from Planner Agent----------\n{state['current_task'].question}")
            logger.info("----------Response from Planner Agent----------")
            logger.info("Planner Response: %s", state['current_task'].question)
            state['agents_status'] = f'{planner_agent_config.agent_name} Awaiting'
            self.called_agent = planner_agent_config.agent_id
            self.responses[planner_agent_config.agent_id].append(("Returned from Planner with a question", state['current_task'].question))
            return {**state}

    def call_human(self, state: SupervisorState):
        human_agent_config = self.agents_config[ProjectAgents.human.agent_id]
        # Display relevant information to the human
        # pprint(f"----------Supervisor current state----------\n{state}")
        # Prompt for input
        if state['current_task'].question != '':
            # Display the current task being performed to the user
            # pprint(f"----------Current Task that needs your assistance to proceed----------\n{state['current_task']}")
            logger.info("----------Current Task that needs your assistance to proceed----------")
            logger.info("Current Task: %r", state['current_task'])
            # Get human input
            human_input = input(f"Please provide additional input for the question:\n{state['current_task'].question}")

            # Append the human input to current_task additional_info
            state['current_task'].additional_info += '\nHuman_Response:\n' + human_input

            # Update the project status back to executing
            self.project_status = PStatus.EXECUTING.value

            # Add the human responses to the rag cache for future queries and maintain a copy in state too
            human_feedback = (state['current_task'].question, f'Response from Human: {human_input}')
            state['human_feedback'] += [human_feedback]
            self.rag_cache.add(state['current_task'].question, human_input)

        else:
            # print("----------Unable to handle Human Feedback currently so ending execution----------")
            logger.info("----------Unable to handle Human Feedback currently so ending execution----------")
            # exit()

        human_input = input(f"Please provide additional input for the question:\n{state['current_task'].question}")

        # Process the input and update the state
        state['human_feedback'] += [human_input]
        self.project_status = PStatus.EXECUTING.value
        # state.human_feedback = human_input
        return {**state}

    # def update_state(self, state: SupervisorState):
    #     # TODO: Imple Update_state_mechanism
    #     pass
    
    def pick_next_task(self, state):
        if len(state['tasks']) is None:
            return None
        else:
            # next_task = Task(description=self.tasks.pop(), task_status=Status.NEW.value, additional_info='', question='')
            next_task = state['tasks'].pop(0)
            return next_task

    # def call_planner(self, state: SupervisorState) -> SupervisorState:
    #     # Implement the logic to call the Planner agent
        # planner_result = self.team_members['Planner'].invoke(state['current_task'])
    #     state['current_task'] = planner_result
    #     state['agents_status'] = 'Planner completed'
    #     return state

    # def update_state(self, state: SupervisorState) -> SupervisorState:
    #     # Update the overall state based on the current task and agent status
    #     state['tasks'].append(state['current_task'])
    #     if all(task.task_status == ProgressState.DONE for task in state['tasks']):
    #         return END
    #     return state

    def delegator(self, state: SupervisorState) -> str:
        # Decide which agent to call next based on the current state
        if self.project_status == PStatus.NEW.value:
            # self.calling_agent = 'Supervisor'
            # self.project_status = PStatus.INITIAL.value
            return 'call_rag'
        elif self.project_status == PStatus.INITIAL.value:
            if self.calling_agent==ProjectAgents.supervisor.agent_id:
                return 'call_architect'
            # self.calling_agent = 'Supervisor'
            else:
                return 'call_rag'
        elif self.project_status==PStatus.MONITORING.value and "RAG_Response" not in state['current_task'].additional_info:
            return 'call_rag'
        elif self.project_status==PStatus.MONITORING.value and 'Architect_Response' not in state['current_task'].additional_info:
            return 'call_architect'
        elif self.project_status==PStatus.EXECUTING.value and self.calling_agent!=ProjectAgents.supervisor.agent_id:
            return calling_map[self.calling_agent]
        elif self.project_status==PStatus.EXECUTING.value and (self.called_agent==ProjectAgents.architect.agent_id or self.called_agent==ProjectAgents.supervisor.agent_id):
            return 'call_planner'
        elif self.project_status==PStatus.EXECUTING.value and (self.called_agent==ProjectAgents.planner.agent_id or self.called_agent==ProjectAgents.coder.agent_id):
            return 'call_coder'
        # elif self.project_status==PStatus.EXECUTING.value and self.called_agent=='Coder':
        #     return 'call_coder'
        elif self.project_status==PStatus.HALTED.value:
            return 'Human'

        # elif state['current_task'].task_status == Status.AWAITING.value:
        #     if self.called_agent == 'Architect':
        #         return 'call_rag'
        #     else:
        #         return 'call_architect'
        # elif self.called_agent != 'Architect' and state['current_task'].task_status == Status.NEW.value:
        #     self.calling_agent = 'Supervisor'
        #     return 'call_architect'
        # elif (self.called_agent == 'Architect' and state['current_task'].task_status == Status.DONE.value and len(self.tasks) is not None) or self.calling_agent == 'Planner':
        #     self.calling_agent = 'Supervisor'
        #     return 'call_planner'
        # elif (self.called_agent == 'Planner' and state['current_task'].task_status == Status.DONE.value) or self.calling_agent == 'Coder':
        #     self.calling_agent = 'Supervisor'
        #     return 'call_coder'
        # else:
        #     return 'Human'

        # elif state['current_task'].task_status == Status.AWAITING.value:
        #     self.calling_agent
        # elif state['current_task'].task_status == Status.AWAITING.value:
        #     return 'call_rag'
        # if state['current_task'].task_status == Status.NEW:
        #     return "call_architect"
        # elif state['current_task'].task_status == Status.AWAITING:
        #     return "Planner"
        # elif state['current_task'].task_status == Status.INPROGRESS:
        #     if "design" in state['current_task'].task.lower():
        #         return "Architect"
        #     elif "code" in state['current_task'].task.lower():
        #         return "Coder"
        # return "update_state"

    # def get_additional_info(self, state: SupervisorState):
    #     question = state['current_task']['additional_info']
    #     additional_info = self.team_members['RAG'].invoke({'question':question})
    #     state['current_task']['additional_info'] = additional_info
    #     state['rag_retrieval'] = additional_info
    #     return {**state}
    #     architect_state = self.team_members['RAG'].agent.state

    # def delegate_task(self, state: SupervisorState):
    #     pass

    # def call_architect(self, state: SupervisorState):
    #     pass
