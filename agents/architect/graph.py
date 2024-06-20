"""
Architect Agent
"""
from langgraph.graph import END
from langgraph.graph import StateGraph

from agents.architect.agent import ArchitectAgent
from agents.architect.state import ArchitectState

class Architect:
    def __init__(self, llm) -> None:
        self.agent = ArchitectAgent(llm)
        self.app = self.define_graph()

    def define_graph(self) -> any:
        # Graph
        architect_flow = StateGraph(ArchitectState)

        # node
        architect_flow.add_node(self.agent.name, self.agent.node)

        # edges
        architect_flow.add_conditional_edges(
            self.agent.name,
            self.agent.router, 
            {
                self.agent.name: self.agent.name,
                END:END
            }
        )

        architect_flow.set_entry_point(self.agent.name)
        return architect_flow.compile()
    

if __name__ == "__main__":
    from langchain_openai import ChatOpenAI
    from pprint import pprint
    import json

    def read_input_json(file_path) -> str:
        """Reads JSON data from a file and returns it as a string.

        Args:
            file_path: The path to the JSON file.

        Returns:
            A string representation of the JSON data.
        """
        with open(file_path, 'r') as user_input_file:
            data = json.load(user_input_file)
        
        user_input = json.dumps(data)
        license_txt = data["LICENSE_TEXT"]

        return user_input, license_txt
    
    llm = ChatOpenAI(model="gpt-4o-2024-05-13", temperature=0, max_retries=5, streaming=True, seed=4000)

    try:
        app = Architect(llm=llm)
        print("here1")
        user_input, license_text = read_input_json("../configs/rest_api.json")

        new_state = {
            "error": False,
            "tasks": [],
            "project_folders":"",
            "current_task": {
                'task': '',
                'state': ''
            },
            "project_state": 'NEW',
            "messages": []
        }

        events = app.stream(
            {   
                **new_state,
                "messages": [
                    (   "user",
                        f"Create this project for me in '/opt/genpod/output'." 
                        f"Requirements are {user_input}."
                        f"{license_text} must be present at the top of each file created as part of the project." 
                        "Once you code it up, finish."
                    )
                ]
            },
            # Maximum number of steps to take in the graph and the thread ID to be used to persist the memory.
            {
                "recursion_limit": 200,
                "configurable": {"thread_id": "1"}
            },
        )

        print("here")
        for s in events:
            pprint(s)

    except AssertionError as ae:
        print(f"Assertion Error Occured: {ae}")