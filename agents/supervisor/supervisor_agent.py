from langchain_core.output_parsers import StrOutputParser
from langchain_core.output_parsers import JsonOutputParser
from agents.supervisor.supervisor_state import SupervisorState
from agents.architect.graph import Architect
from agents.rag_workflow.rag_graph import RAGWorkFlow
from models.enums import ProgressState
from agents.supervisor.supervisor_models import TaskDetails

class SupervisorAgent():
    def __init__(self, llm, user_prompt):
        self.llm = llm
        self.calling_agent = None
        self.called_agent = None
        self.team_members = {'Architect':None,
                             'RAG':None,
                             'Coder':None,
                             'Planner':None}
        
        self.state = {}
        self.user_prompt = user_prompt
    
    def instantiate_team_members(self, state: SupervisorState):
        for member,_ in self.team_members.items():
            if member=='Architect':
                self.team_members[member] = Architect(self.llm)
            elif member=='RAG':
                self.team_members[member] = RAGWorkFlow(self.llm,
                                                        collection_name='MISMO-version-3.6-docs',
                                                        persist_directory='C:/Users/vkumar/Desktop/genpod-ai-backend/vector_collections')
            else:
                # TODO: Implement other team members' graph instantiation here.
                # For now, skip other team members.
                continue

        state['team_members'] = {**self.team_members}
        state['original_user_input'] = self.user_prompt
        state['rag_retrieval'] = ''
        state['current_task'] = TaskDetails(task ='retrieve additional context from RAG system',
                                            task_status = ProgressState.NEW.value,
                                            additional_info = '')


    def get_additional_info(self, state: SupervisorState):
        question = state['current_task']['additional_info']
        additional_info = self.team_members['RAG'].invoke({'question':question})
        state['current_task']['additional_info'] = additional_info
        state['rag_retrieval'] = additional_info
        return {**state}
        architect_state = self.team_members['RAG'].agent.state

    def delegate_task(self, state: SupervisorState):
        pass

    def call_architect(self, state: SupervisorState):
        pass
