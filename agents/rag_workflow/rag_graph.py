from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from agents.rag_workflow.rag_state import RAGState
from agents.rag_workflow.rag_agent import RAGAgent

class RAGWorkFlow():
    def __init__(self, llm, collection_name, thread_id=None, persist_directory=None):
        self.agent = RAGAgent(llm, collection_name = collection_name, persist_directory=persist_directory)
        self.rag_workflow = StateGraph(RAGState)
        # Memory for Persistence
        self.thread_id = thread_id

        if thread_id is not None:
            self.memory = SqliteSaver.from_conn_string(":memory:")
        # Define the nodes
        self.rag_workflow.add_node("retrieve", self.agent.retrieve)  # retrieve
        self.rag_workflow.add_node("grade_documents", self.agent.grade_documents)  # grade documents
        self.rag_workflow.add_node("generate", self.agent.generate)  # generate
        self.rag_workflow.add_node("transform_query", self.agent.transform_query)  # transform_query
        self.rag_workflow.add_node("update_state", self.agent.update_state)

        # Build graph
        self.rag_workflow.set_entry_point("retrieve")
        self.rag_workflow.add_edge("retrieve", "grade_documents")
        self.rag_workflow.add_conditional_edges(
            "grade_documents",
            self.agent.decide_to_generate,
            {
                "transform_query": "transform_query",
                "generate": "generate",
            },
        )
        self.rag_workflow.add_edge("transform_query", "retrieve")
        self.rag_workflow.add_conditional_edges(
            "generate",
            self.agent.grade_generation_v_documents_and_question,
            {
                "not supported": "generate",
                "useful": "update_state",
                "not useful": "transform_query",
            },
        )
        self.rag_workflow.add_edge("update_state", END)

        # # Compile
        # self.rag_app = self.rag_workflow.compile()
        if thread_id is not None:
            self.rag_app = self.rag_workflow.compile(checkpointer=self.memory)
        
        else:
            print("You have not set the Thread ID so not persisting the workflow state.")
            self.rag_app = self.rag_workflow.compile()
    
    def get_current_state(self):
        """ Returns the current state dictionary of the agent """
        return self.agent.state


if __name__=="__main__":
    #  Example using in you main graph.
    from langchain_openai import ChatOpenAI
    from pprint import pprint
    from dotenv import load_dotenv
    load_dotenv()

    llm = ChatOpenAI(model="gpt-4o-2024-05-13", temperature=0, max_retries=5, streaming=True, seed=4000)

    # Currently only use this value for collection_name if you have embeded and saved vector into the db with a differnet name then you can use it here.
    collection_name = 'MISMO-version-3.6-docs'

    persist_directory = "C:/Users/vkumar/Desktop/genpod-ai-backend/vector_collections"

    RAG_thread_id = "1"
    try:
        RAG = RAGWorkFlow(llm=llm, collection_name=collection_name, thread_id=RAG_thread_id,  persist_directory=persist_directory)

        rag_input = {"question": "Any question related to MISMO_Standards"}

        result = ''
        for output in RAG.rag_app.stream(rag_input, thread_id= RAG.thread_id):
            for key, value in output.items():
                # Node
                pprint(f"Node '{key}':")
                # Optional: print full state at each node
                # pprint.pprint(value["keys"], indent=2, width=80, depth=None)
                result = value["generation"]
            pprint("\n---\n")
        
        pprint(result)

    except AssertionError as ae:
        print(f"Assertion Error Occured: {ae}")

