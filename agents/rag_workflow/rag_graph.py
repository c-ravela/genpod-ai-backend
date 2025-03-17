import os

from langgraph.graph import END, StateGraph

from agents.base.base_graph import BaseGraph
from agents.rag_workflow.rag_agent import RAGAgent
from agents.rag_workflow.rag_state import RAGState
from llms.llm import LLM


class RAGWorkFlow(BaseGraph[RAGAgent]):

    def __init__(self, graph_id: str, graph_name: str, agent_id: str, agent_name: str, llm: LLM, persistance_db_path: str, collection_name: str, persist_directory: str=None):
        super().__init__(
            graph_id,
            graph_name, 
            RAGAgent(
                agent_id,
                agent_name,
                llm,
                collection_name=collection_name,
                persist_directory=persist_directory
            ),
            persistance_db_path
        )

        self.compile_graph_with_persistence()

    def define_graph(self) -> StateGraph:
        
        rag_workflow = StateGraph(RAGState)

        # Define the nodes
        rag_workflow.add_node("retrieve", self.agent.retrieve)  # retrieve
        rag_workflow.add_node("grade_documents", self.agent.grade_documents)  # grade documents
        rag_workflow.add_node("generate", self.agent.generate)  # generate
        rag_workflow.add_node("transform_query", self.agent.transform_query)  # transform_query
        rag_workflow.add_node("save_analytics", self.agent.save_analytics_record)
        rag_workflow.add_node("update_state", self.agent.update_state)

        # Build graph
        rag_workflow.set_entry_point("retrieve")
        rag_workflow.add_edge("retrieve", "grade_documents")
        rag_workflow.add_conditional_edges(
            "grade_documents",
            self.agent.decide_to_generate,
            {
                "transform_query": "transform_query",
                "generate": "generate",
            },
        )
        # self.rag_workflow.add_edge("transform_query", "retrieve")
        rag_workflow.add_conditional_edges(
            "transform_query",
            lambda x: x["next"],
            {
                "retrieve": "retrieve",
                "update_state": "save_analytics",
            },
        )
        rag_workflow.add_conditional_edges(
            "generate",
            self.agent.grade_generation_v_documents_and_question,
            {
                "not supported": "generate",
                "useful": "save_analytics",
                "not useful": "transform_query",
            },
        )

        rag_workflow.add_edge("save_analytics", "update_state")
        rag_workflow.add_edge("update_state", END)

        return rag_workflow
    
    def get_current_state(self):
        """ Returns the current state dictionary of the agent """
        return self.agent.state


if __name__=="__main__":
    #  Example using in you main graph.
    from pprint import pprint

    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI
    load_dotenv()

    llm = ChatOpenAI(model="gpt-4o-2024-05-13", temperature=0, max_retries=5, streaming=True, seed=4000)

    # Currently only use this value for collection_name if you have embeded and saved vector into the db with a differnet name then you can use it here.
    collection_name = 'MISMO-version-3.6-docs'

    persist_directory = os.path.join(os.getcwd(), "../../vector_collections")

    RAG_thread_id = "1"
    try:
        RAG = RAGWorkFlow(llm=llm, collection_name=collection_name, thread_id=RAG_thread_id,  persist_directory=persist_directory)

        rag_input = {"question": "Any question related to MISMO_Standards"}

        result = ''
        for output in RAG.app.stream(rag_input, thread_id= RAG.thread_id):
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
