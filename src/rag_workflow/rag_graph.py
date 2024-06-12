from langgraph.graph import StateGraph, END
from .rag_state import RAGState
from .rag_agent import RAGAgent

class RAGWorkFlow():
    def __init__(self, llm, collection_name, persist_directory=None):
        self.agent = RAGAgent(llm, collection_name = collection_name, persist_directory=persist_directory)
        rag_workflow = StateGraph(RAGState)
        # Define the nodes
        rag_workflow.add_node("retrieve", self.agent.retrieve)  # retrieve
        rag_workflow.add_node("grade_documents", self.agent.grade_documents)  # grade documents
        rag_workflow.add_node("generate", self.agent.generate)  # generate
        rag_workflow.add_node("transform_query", self.agent.transform_query)  # transform_query

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
        rag_workflow.add_edge("transform_query", "retrieve")
        rag_workflow.add_conditional_edges(
            "generate",
            self.agent.grade_generation_v_documents_and_question,
            {
                "not supported": "generate",
                "useful": END,
                "not useful": "transform_query",
            },
        )

        # Compile
        self.rag_app = rag_workflow.compile()

if __name__=="__main__":
    #  Example using in you main graph.
    from langchain_openai import ChatOpenAI
    from pprint import pprint

    llm = ChatOpenAI(model="gpt-4o-2024-05-13", temperature=0, max_retries=5, streaming=True, seed=4000)

    # Currently only use this value for collection_name if you have embeded and saved vector into the db with a differnet name then you can use it here.
    collection_name = 'MISMO-version-3.6-docs'

    persist_directory = 'src/vector_collections'

    try:
        RAG = RAGWorkFlow(llm=llm, collection_name=collection_name, persist_directory=persist_directory)

        input = {"question": "Any question related to MISMO_Standards"}

        result = ''
        for output in RAG.rag_app.stream(input):
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
