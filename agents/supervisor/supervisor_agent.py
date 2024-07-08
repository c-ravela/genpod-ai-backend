from agents.supervisor.supervisor_state import SupervisorState
from agents.architect.graph import ArchitectGraph
from agents.rag_workflow.rag_graph import RAGWorkFlow
from agents.planner.planner_graph import PlannerWorkFlow
from models.constants import Status, PStatus
from models.models import Task
from typing import Dict, List, Union, Tuple
from configs.project_path import set_project_path
from configs.supervisor_config import calling_map
from utils.fuzzy_rag_cache import FuzzyRAGCache
import ast
from agents.supervisor.supervisor_prompts import SupervisorPrompts
from agents.supervisor.supervisor_models import QueryList
from pydantic import ValidationError
from langchain_openai import ChatOpenAI
from pprint import pprint

class SupervisorAgent():
    def __init__(self, llm, collections, members, memberids, user_input, rag_try_limit, project_path):
        self.llm = llm
        self.collections = collections
        self.members = members
        self.memberids = memberids
        self.rag_try_limit = rag_try_limit
        self.project_path = project_path
        self.rag_cache = FuzzyRAGCache()
        self.rag_cache_building = ''

        self.calling_agent = None
        self.called_agent = None
        self.team_members: Dict[str, Union[object, None]] = {x: None for x in self.members}
        # {
        #     'Architect': None,
        #     'RAG': None,
        #     'Coder': None,
        #     'Planner': None
        # }
        self.state = {}
        self.user_prompt = user_input
        # self.project_status = None
        self.responses: Dict[str, List[Tuple[str, Task]]] = {
            'Architect': [],
            'RAG': [],
            'Coder': [],
            'Planner': []
        }
        self.tasks = []
        self.prompts = SupervisorPrompts()
        self.project_status = None
        self.project_init_questionaire = SupervisorPrompts.init_rag_questionaire_prompt | self.llm
        self.evaluation_chain = SupervisorPrompts.follow_up_questions | self.llm

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
        #             result = self.team_members['RAG'].rag_app.invoke({'question': req_query,'iteration_count':self.rag_try_limit}, {'configurable':{'thread_id':self.memberids['RAG']}})
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
                    print(f"Cache hit for query: {req_query}")
                    rag_response = result
                else:
                    print(f"Cache miss for query: {req_query}")
                    print(f'----------RAG Agent Called to Query----------\n{req_query}')
                    result = self.team_members['RAG'].rag_app.invoke({'question': req_query, 'iteration_count': self.rag_try_limit}, {'configurable': {'thread_id': self.memberids['RAG']}})
                    rag_response = result['generation']
                    self.rag_cache.add(req_query, rag_response)
                    print(f'----------RAG Agent Response----------\n{rag_response}')
                
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
                            print(f"\n----------Follow-up query needed----------\n{follow_up_query}")
                            
                            # Ask the follow-up query to the RAG agent
                            follow_up_result = self.team_members['RAG'].rag_app.invoke({'question': follow_up_query, 'iteration_count': self.rag_try_limit}, {'configurable': {'thread_id': self.memberids['RAG']}})
                            follow_up_response = follow_up_result['generation']
                            self.rag_cache.add(follow_up_query, follow_up_response)
                            
                            final_response += f"Question: {req_query}\nInitial Answer: {rag_response}\nFollow-up Question: {follow_up_query}\nFollow-up Answer: {follow_up_response}\n\n"
                        else:
                            print("Unexpected evaluation result format.")
                            final_response += f"Question: {req_query}\nAnswer: {rag_response}\n\n"
            return final_response
        else:
            return 'Failed to initialize project'

    def instantiate_team_members(self, state: SupervisorState):
        for member,_ in self.team_members.items():
            if member=='Architect':
                self.team_members[member] = ArchitectGraph(ChatOpenAI(model="gpt-4o-2024-05-13", temperature=0.3, max_retries=5, streaming=True, seed=4000, top_p=0.4))
            elif member=='RAG':
                # We can to implement a scenario where we are able to use appropriate collection_name from the list of collections based on the user_input
                # This will probably mechanism should probably go inside ragworkflow implementation. For now lets keep it simple
                self.team_members[member] = RAGWorkFlow(ChatOpenAI(model="gpt-4o-2024-05-13", temperature=0, max_retries=5, streaming=True, seed=4000, top_p=0.3),
                                                        collection_name=list(self.collections.keys())[0],
                                                        thread_id=self.memberids[member],
                                                        persist_directory=self.collections[list(self.collections.keys())[0]])
            elif member=='Planner':
                self.team_members[member] = PlannerWorkFlow(ChatOpenAI(model="gpt-4o-2024-05-13", temperature=0.3, max_retries=5, streaming=True, seed=4000, top_p=0.6),
                                                            thread_id=self.memberids[member])
            else:
                # TODO: Implement other team members' graph instantiation here.
                # For now, skip other team members.
                continue

        # state['team_members'] = {**self.team_members}
        state['original_user_input'] = self.user_prompt
        state['project_path'] = set_project_path(self.project_path)
        state['rag_retrieval'] = ''
        state['current_task'] = Task(description='retrieve additional context from RAG system',
                                     task_status = Status.NEW.value,
                                     additional_info = '',
                                     question=self.user_prompt)
        # state['agents_status'] = 'New'
        message = ('user','Start new Project')

        state['messages'] += [message]
        self.project_status = PStatus.NEW.value
        self.rag_cache_building = self.build_rag_cache(state['original_user_input'])
        return {**state}

    def call_rag(self, state: SupervisorState) -> SupervisorState:
        question = state['current_task'].question
        try:
            message = ('Assistant', 'Calling RAG Agent')
            state['messages'] += [message]
            print("----------Getting Additional information from RAG Agent----------")
            # Check in cache first
            result = self.rag_cache.get(question)
            if result is not None:
                print(f"Cache hit for query: \n{question}")
                message = ('Assistant', f'Response from RAG: {result}')
                state['rag_query_answer'] = True
                # return result
            else:
                print(f"Cache miss for query: \n{question}")
                # result = your_rag_query_function(query)  # Replace with your actual RAG query function
            # return result
                additional_info = self.team_members['RAG'].rag_app.invoke({'question': question,'iteration_count':self.rag_try_limit},{'configurable':{'thread_id':self.memberids['RAG']}})
                result = additional_info['generation']
                state['rag_query_answer'] = additional_info['query_answered']
                self.rag_cache.add(question, result)
                message = ('Assistant', f'Response from RAG: {result}')
            state['messages'] += [message]
            print(f"----------Response from RAG Agent----------\n{result}")
        except Exception as e:
            raise(e)
        if state['current_task'].task_status.value == Status.NEW.value:
            state['current_task'].additional_info = result + "\n" + self.rag_cache_building
            state['current_task'].task_status = Status.DONE
            state['rag_retrieval'] = result + "\n" + self.rag_cache_building
            state['agents_status'] = 'RAG completed'
            self.called_agent = 'RAG'
            self.responses['RAG'].append(("Returned from RAG database",state['current_task']))
            return {**state}

        elif state['current_task'].task_status.value == Status.AWAITING.value:
            #  This mean the query RAG Agent to get additional information for another agent which wikk be present in called agent and that will and should never be updated when returning
            # if additional_info['generation'] != "I don't have any additional information about the question.":
            state['current_task'].additional_info += "\nRAG_Response:\n" + result
            state['rag_retrieval'] += result
            state['agents_status'] = 'RAG completed'
            self.called_agent = 'RAG'
            self.responses['RAG'].append(("Returned from RAG database serving a query",state['current_task']))
            # state['rag_query_answer'] = additional_info['query_answered']
            return {**state}
        
        return {**state}
            
    def call_architect(self, state: SupervisorState) -> SupervisorState:
        # Implement the logic to call the Architect agent
        if self.project_status == PStatus.INITIAL.value:
            message = ('Assistant', 'Calling Architect Agent')
            state['messages'] += [message]
            print("----------Calling Architect----------")
            
            architect_result = self.team_members['Architect'].app.invoke({'current_task':state['current_task'],
                                                                          'project_status':self.project_status,
                                                                          'user_request': state['original_user_input'],
                                                                          'generated_project_path':state['project_path'],
                                                                          'user_requested_standards':state['current_task'].additional_info,
                                                                          'messages':[]},
                                                                         {'configurable':{'thread_id':self.memberids['Architect']}})

            # architect_state = self.team_members['Architect'].app.get_current_state()
            message = ('Assistant', f'Response from Architect: {architect_result['tasks']}')
            state['messages'] += [message]
            print(f"----------Response from Architect Agent----------\n{architect_result['tasks']}")
            # Temporary validation this needs to be done by architect. Remove it once architect has implemented this.
            # if len(architect_result['tasks']) is not None:
            #     architect_result['current_task'].task_status = Status.DONE
            if architect_result['current_task'].task_status.value == Status.DONE.value:
                self.project_status = PStatus.EXECUTING.value
                state['current_task'] = architect_result['current_task']
                state['agents_status'] = 'Architect completed'
                self.responses['Architect'].append(("Returned from Architect", architect_result['tasks']))
                state['tasks'] = architect_result['tasks']
                state['requirements_doc'] = architect_result['requirements_overview']
                self.called_agent = 'Architect'
                return {**state}
            else:
                #  TODO: if task_status=='AWAITING', that means Current task could not be completed by architect call supervisor to deal with the same task
                # self.project_status = PStatus.MONITORING.value
                state['current_task'] = architect_result['current_task']
                state['agents_status'] = 'Architect Awaiting'
                self.responses['Architect'].append(("Returned from Architect with a question:", architect_result['current_task'].question))
                self.called_agent = 'Architect'
                return {**state}
            
        elif self.project_status == PStatus.MONITORING.value:
            # Need to query Architect to get additional information for another agent which will be present in called agent and that will never be updated when returning
            print("----------Querying Architect----------")
            architect_result = self.team_members['Architect'].app.invoke({'current_task':state['current_task'],
                                                                          'project_status':self.project_status,
                                                                          'user_request': state['original_user_input'],
                                                                          'generated_project_path':state['project_path'],
                                                                          'user_requested_standards':state['current_task'].additional_info,
                                                                          'messages':[]},
                                                                         {'configurable':{'thread_id':self.memberids['Architect']}})
            print(f"----------Response from Architect Agent----------\n{architect_result['current_task']}")
            # architect_state = self.team_members['Architect'].app.get_current_state()
            if architect_result['query_answered'] is True:
                # self.project_status = PStatus.EXECUTING.value
                # state['current_task'].additional_info += "\nArchitect_Response:\n" + architect_state['current_task'].additional_info
                state['agents_status'] = 'Architect completed'
                self.responses['Architect'].append(("Returned from Architect serving a Query", architect_result['current_task']))
                self.called_agent = 'Architect'
                state['current_task'] = architect_result['current_task']
                return {**state}
            elif state['rag_query_answer'] is False and architect_result['query_answered'] is False:
                # Additional Human input is needed
                state['current_task'] = architect_result['current_task']
                self.project_status = PStatus.HALTED.value
        
        return {**state}

    def call_coder(self, state: SupervisorState) -> SupervisorState:
        # Implement the logic to call the Coder agent
        coder_result = self.team_members['Coder'].invoke(state['current_task'])
        coder_state = self.team_members['Coder'].get_state()
        state['current_task'] = coder_state['current_task']
        state['agents_status'] = 'Coder completed'
        self.called_agent = 'Coder'
        self.responses['Coder'].append(("Returned from Coder",state['current_task']))
        return {**state}

    def call_supervisor(self, state: SupervisorState):
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
            self.calling_agent = 'Supervisor'
            return {**state}
        elif self.project_status == PStatus.INITIAL.value:
            # If Architect has any queries during project Initial Stage which is common then we only want to call rag and send that response to architect
            if state['current_task'].task_status.value == Status.AWAITING.value and "RAG_Response" not in state['current_task'].additional_info:
                self.calling_agent = self.called_agent
            else:
                self.calling_agent = 'Supervisor'
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
        elif self.project_status == PStatus.EXECUTING.value and state['current_task'].task_status.value == Status.DONE.value:
            # self.tasks = state['tasks']
            new_task = self.pick_next_task(state)
            if new_task is None:
                self.project_status = PStatus.HALTED.value
            state['current_task'] = new_task
            state['current_task'].additional_info = state['requirements_doc'] + '\n' + state['rag_retrieval']
            self.calling_agent = 'Supervisor'
            return {**state}
        else:
            return {**state}

    def call_planner(self, state: SupervisorState):
        # TODO: Implement Planner Agent
        # Implement the logic to call the Coder agent
        # response = self.team_members['Planner'].update_task(state['current_task'])
        print("----------Calling Planner----------")
        planner_result = self.team_members['Planner'].planner_app.invoke({'current_task':state['current_task']},{'configurable':{'thread_id':self.memberids['Planner']}})
        # planner_state = self.team_members['Planner'].planner_app.get_state()
        state['current_task'] = planner_result['response'][-1]
        if state['current_task'].task_status.value == Status.DONE.value:
            print(f"----------Response from Planner Agent----------\n{planner_result['deliverable_backlog_map']}")
            state['agents_status'] = 'Planner completed'
            self.called_agent = 'Planner'
            self.responses['Planner'].append(("Returned from Planner",state['current_task']))
        elif state['current_task'].task_status.value == Status.INPROGRESS.value:
            # TODO: Call coder to work on workpackages of a deliverable.
            pass
        else:
            print(f"----------Response from Planner Agent----------\n{state['current_task'].question}")
            state['agents_status'] = 'Planner Awaiting'
            self.called_agent = 'Planner'
            self.responses['Planner'].append(("Returned from Planner with a question",state['current_task'].question))
            return {**state}


    def call_human(self, state: SupervisorState):
        # Display relevant information to the human
        # pprint(f"----------Supervisor current state----------\n{state}")
        # Prompt for input
        if state['current_task'].question != '':
            # Display the current task being performed to the user
            pprint(f"----------Current Task that needs your assistance to proceed----------\n{state['current_task']}")

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
            print("----------Unable to handle Human Feedback currently so ending execution----------")
            exit()

        # Process the input and update the state
        state.human_feedback = human_input
        return state

    def update_state(self, state: SupervisorState):
        # TODO: Imple Update_state_mechanism
        pass
    
    def pick_next_task(self, state):
        if len(state['tasks']) is None:
            return None
        else:
            # next_task = Task(description=self.tasks.pop(), task_status=Status.NEW.value, additional_info='', question='')
            next_task = state['tasks'].pop(0)
            return next_task

    # def call_planner(self, state: SupervisorState) -> SupervisorState:
    #     # Implement the logic to call the Planner agent
    #     planner_result = self.team_members['Planner'].invoke(state['current_task'])
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
            if self.calling_agent=='Supervisor':
                return 'call_architect'
            # self.calling_agent = 'Supervisor'
            else:
                return 'call_rag'
        elif self.project_status==PStatus.MONITORING.value and "RAG_Response" not in state['current_task'].additional_info:
            return 'call_rag'
        elif self.project_status==PStatus.MONITORING.value and 'Architect_Response' not in state['current_task'].additional_info:
            return 'call_architect'
        elif self.project_status==PStatus.EXECUTING.value and self.calling_agent!='Supervisor':
            return calling_map[self.calling_agent]
        elif self.project_status==PStatus.EXECUTING.value and self.called_agent=='Architect':
            return 'call_planner'
        elif self.project_status==PStatus.EXECUTING.value and self.called_agent=='Planner':
            return 'call_coder'
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
