from agents.supervisor.supervisor_state import SupervisorState
from agents.architect.graph import ArchitectGraph
from agents.rag_workflow.rag_graph import RAGWorkFlow
from agents.planner.planner_graph import PlannerWorkFlow
from models.constants import Status, PStatus
from models.models import Task
from typing import Dict, List, Union, Tuple
from configs.project_path import set_project_path

from agents.supervisor.supervisor_prompts import SupervisorPrompts
class SupervisorAgent():
    def __init__(self, llm, collections, members, memberids, user_input, rag_try_limit, project_path):
        self.llm = llm
        self.collections = collections
        self.members = members
        self.memberids = memberids
        self.rag_try_limit = rag_try_limit
        self.project_path = project_path

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

    def instantiate_team_members(self, state: SupervisorState):
        for member,_ in self.team_members.items():
            if member=='Architect':
                self.team_members[member] = ArchitectGraph(self.llm)
            elif member=='RAG':
                # We can to implement a scenario where we are able to use appropriate collection_name from the list of collections based on the user_input
                # This will probably mechanism should probably go inside ragworkflow implementation. For now lets keep it simple
                self.team_members[member] = RAGWorkFlow(self.llm,
                                                        collection_name=list(self.collections.keys())[0],
                                                        thread_id=self.memberids[member],
                                                        persist_directory=self.collections[list(self.collections.keys())[0]])
            elif member=='Planner':
                self.team_members[member] = PlannerWorkFlow(self.llm,
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
        return {**state}

    def call_rag(self, state: SupervisorState) -> SupervisorState:
        question = state['current_task'].question
        try:
            message = ('Assistant', 'Calling RAG Agent')
            state['messages'] += [message]
            additional_info = self.team_members['RAG'].rag_app.invoke({'question': question,'iteration_count':self.rag_try_limit},{'configurable':{'thread_id':self.memberids['RAG']}})
            message = ('Assistant', f'Response from RAG: {additional_info['generation']}')
            state['messages'] += [message]
        except Exception as e:
            raise(e)
        if state['current_task'].task_status.value == Status.NEW.value:
            state['current_task'].additional_info = additional_info['generation']
            state['current_task'].task_status = Status.DONE
            state['rag_retrieval'] = additional_info['generation']
            state['agents_status'] = 'RAG completed'
            self.called_agent = 'RAG'
            self.responses['RAG'].append(("Returned from RAG database",state['current_task']))
            return {**state}

        elif state['current_task'].task_status.value == Status.AWAITING.value:
            #  This mean the query RAG Agent to get additional information for another agent which wikk be present in called agent and that will and should never be updated when returning
            # if additional_info['generation'] != "I don't have any additional information about the question.":
            state['current_task'].additional_info += "\nRAG_Response:\n" + additional_info['generation']
            state['rag_retrieval'] = additional_info['generation']
            state['agents_status'] = 'RAG completed'
            self.called_agent = 'RAG'
            self.responses['RAG'].append(("Returned from RAG database serving a query",state['current_task']))
            state['rag_query_answer'] = additional_info['query_answered']
            return {**state}
        
        return {**state}
            
    def call_architect(self, state: SupervisorState) -> SupervisorState:
        # Implement the logic to call the Architect agent
        if self.project_status == PStatus.INITIAL.value:
            architect_result = self.team_members['Architect'].app.invoke({'current_task':state['current_task'],'project_status':self.project_status, 'user_request': state['original_user_input'], 'generated_project_path':state['project_path'], 'messages':[]},
                                                                         {'configurable':{'thread_id':self.memberids['Architect']}})
            architect_state = self.team_members['Architect'].app.get_current_state()
            if architect_state['current_task'].task_status.value == Status.DONE.value:
                self.project_status = PStatus.EXECUTING.value
                state['current_task'] = architect_state['current_task']
                state['agents_status'] = 'Architect completed'
                self.responses['Architect'].append(("Returned from Architect", state['current_task']))
                state['tasks'] = architect_state['tasks']
                self.called_agent = 'Architect'
                return {**state}
            else:
                #  TODO: if task_status=='AWAITING', that means Current task could not be completed by architect call supervisor to deal with the same task
                # self.project_status = PStatus.MONITORING.value
                pass

        elif self.project_status == PStatus.MONITORING.value:
            # Need to query Architect to get additional information for another agent which will be present in called agent and that will never be updated when returning
            architect_result = self.team_members['Architect'].app.invoke(state['current_task'],{'configurable':{'thread_id':self.memberids['Architect']}})
            architect_state = self.team_members['Architect'].app.get_current_state()
            if architect_state['query_answered'] is True:
                # self.project_status = PStatus.EXECUTING.value
                # state['current_task'].additional_info += "\nArchitect_Response:\n" + architect_state['current_task'].additional_info
                state['agents_status'] = 'Architect completed'
                self.responses['Architect'].append(("Returned from Architect serving a Query", state['current_task']))
                self.called_agent = 'Architect'
                state['current_task'] = architect_state['current_task']
                return {**state}
            elif state['rag_query_answer'] is False and architect_state['query_answered'] is False:
                # Additional Human input is needed
                state['current_task'] = architect_state['current_task']
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
                self.project_status = PStatus.INITIAL.value
            self.calling_agent = 'Supervisor'
            return {**state}
        elif self.project_status == PStatus.INITIAL.value:
            # Lets first create the new task for initial phase of the project
            _description = self.prompts.architect_call_prompt
            _task_status = Status.NEW.value
            _additional_info = state['rag_retrieval']
            _question=''
            state['current_task'] = Task(description=_description,task_status=_task_status,additional_info=_additional_info,question=_question)
            self.calling_agent = 'Supervisor'
            return {**state}
        elif self.project_status == PStatus.EXECUTING.value and state['current_task'].task_status.value==Status.AWAITING.value:
            self.project_status = PStatus.MONITORING.value
            self.calling_agent = self.called_agent
            return {**state}
        elif self.project_status == PStatus.MONITORING.value:
            if "RAG_Response" in state['current_task'].additional_info and "Architect_Response" in state['current_task'].additional_info:
                self.project_status = PStatus.EXECUTING.value
            # else:
            #     self.project_status = PStatus.HALTED.value
            return {**state}
        elif self.project_status == PStatus.EXECUTING.value and state['current_task'].task_status.value == Status.DONE.value:
            # TODO: Add condition to halt when RAG and Architect cannot answer the question.
            new_task = self.pick_next_task()
            if new_task is None:
                self.project_status = PStatus.HALTED.value
            state['current_task'] = new_task
            self.calling_agent = 'Supervisor'
            return {**state}
        else:
            return {**state}

    def call_planner(self, state: SupervisorState):
        # TODO: Implement Planner Agent
        # Implement the logic to call the Coder agent
        response = self.team_members['Planner'].update_task(state['current_task'])
        planner_result = self.team_members['Planner'].planner_app.invoke({'current_task':state['current_task']},{'configurable':{'thread_id':self.memberids['Planner']}})
        planner_state = self.team_members['Planner'].planner_app.get_state()
        state['current_task'] = planner_state['current_task']
        state['agents_status'] = 'Planner completed'
        self.called_agent = 'Planner'
        self.responses['Planner'].append(("Returned from Planner",state['current_task']))
        return {**state}


    def call_human(self, state: SupervisorState):
        # TODO: Implement Human_in_the_loop
        pass

    def update_state(self, state: SupervisorState):
        # TODO: Imple Update_state_mechanism
        pass
    
    def pick_next_task(self):
        if len(self.tasks) is None:
            return None
        else:
            next_task = Task(description=self.tasks.pop(), task_status=Status.NEW.value, additional_info='', question='')
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
            # self.calling_agent = 'Supervisor'
            return 'call_architect'
        elif self.project_status==PStatus.MONITORING.value and "RAG_Response" not in state['current_task'].additional_info:
            return 'call_rag'
        elif self.project_status==PStatus.MONITORING.value and 'Architect_Response' not in state['current_task'].additional_info:
            return 'call_architect'
        elif self.project_status==PStatus.EXECUTING.value and self.calling_agent!='Supervisor':
            return self.calling_agent
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
