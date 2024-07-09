from agents.planner.planner_state import PlannerState
from agents.planner.planner_agent import PlannerAgent
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from models.models import Task
from utils.logs.logging_utils import logger

class PlannerWorkFlow():
    def __init__(self, llm, thread_id=None):
        self.agent = PlannerAgent(llm=llm)
        self.thread_id = thread_id

        if thread_id is not None:
            self.memory = SqliteSaver.from_conn_string(":memory:")
        
        # self.new_task : Task = None
        self.planner_workflow = StateGraph(PlannerState, config_schema=Task)
        # Define the nodes
        # self.planner_workflow.add_node("new_deliverable_check", self.agent.new_deliverable_check)
        self.planner_workflow.add_node("backlog_planner", self.agent.backlog_planner)  # retrieve
        self.planner_workflow.add_node("requirements_developer", self.agent.requirements_developer)  # grade documents
        self.planner_workflow.add_node("response_generator",self.agent.generate_response)
        self.planner_workflow.add_node("update_state", self.agent.update_state)

        # Build graph
        self.planner_workflow.set_conditional_entry_point(self.agent.new_deliverable_check,
                                                          {"backlog_planner": "backlog_planner",
                                                           "requirements_developer": "requirements_developer"})

        # self.planner_workflow.set_conditional_entry_point(
        #     self.agent.new_deliverable_check,
        #     {
        #         "yes": "backlog_planner",
        #         "no": "requirements_developer"
        #     }
        # )
        self.planner_workflow.add_edge("backlog_planner", "requirements_developer")
        self.planner_workflow.add_edge("requirements_developer", "update_state")
        self.planner_workflow.add_edge("update_state","response_generator")
        self.planner_workflow.add_edge("response_generator", END)

        # Compile
        # Compile
        if thread_id is not None:
            self.planner_app = self.planner_workflow.compile(checkpointer=self.memory)
        
        else:
            # print("You have not set the Thread ID so not persisting the workflow state.")
            logger.info("You have not set the Thread ID so not persisting the workflow state.")
            self.planner_app = self.planner_workflow.compile()
        # self.planner_app = self.planner_workflow.compile()

    def get_current_state(self):
        """ Returns the current state dictionary of the agent """
        return self.agent.state

    def update_task(self, incoming_task: Task):
        try:
            self.agent.current_task = incoming_task
            return "Successfully added the task to memory"
        except: 
            return "Unable to add the task to memory"
