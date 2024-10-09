from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from agents.agent.agent import Agent
from agents.rag_workflow.rag_state import RAGState
from configs.supervisor_config import RAG_TRY_LIMIT
from llms.llm import LLM
from prompts.rag_prompts import RAGPrompts
from utils.logs.logging_utils import logger


class RAGAgent(Agent[RAGState, RAGPrompts]):
    def __init__(self, agent_id: str, agent_name: str, llm: LLM, collection_name: str, persist_directory: str=None):
        assert persist_directory is not None, "Currently only Local Chroma VectorDB is supported"
        
        super().__init__(
            agent_id,
            agent_name,
            RAGState(),
            RAGPrompts(),
            llm
        )

        self.iteration_count = RAG_TRY_LIMIT
        self.mismo_vectorstore = Chroma(
            collection_name = collection_name,
            persist_directory = persist_directory,
            embedding_function = OpenAIEmbeddings()
        )
        self.retriever = self.mismo_vectorstore.as_retriever(search_kwargs={'k': 20})
        
        self.max_hallucination = None
        
    def retrieve(self, state: RAGState):
        """
        Retrieve documents

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, documents, that contains retrieved documents
        """
        # print("----RETRIEVE----")
        logger.info("----RETRIEVE----")
        question = state["question"]
        if self.max_hallucination is None:
            self.max_hallucination = state['max_hallucination']

        # Retrieval
        documents = self.retriever.invoke(question)
        return {**state, "documents": documents, "question": question}

    def generate(self, state: RAGState):
        """
        Generate answer

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): New key added to state, generation, that contains LLM generation
        """
        # print("----GENERATE----")
        
        logger.info("----GENERATE----")
        question = state["question"]
        documents = state["documents"]
        state['query_answered'] = True
        

        # RAG generation
        llm_output = self.llm.invoke(self.prompts.rag_generation_prompt, {
                "context": documents, 
                "question": question
            },
            'string'
        )
        return {**state, "documents": documents, "question": question, "generation": llm_output.response}

    def grade_documents(self, state: RAGState):
        """
        Determines whether the retrieved documents are relevant to the question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates documents key with only filtered relevant documents
        """

        # print("----CHECK DOCUMENT RELEVANCE TO QUESTION----")
        logger.info("----CHECK DOCUMENT RELEVANCE TO QUESTION----")
        question = state["question"]
        documents = state["documents"]

        # Score each doc
        filtered_docs = []
        for d in documents:
            llm_output = self.llm.invoke(self.prompts.retriever_grader_prompt, {
                    "question": question, 
                    "document": d.page_content
                }, 
                'json'
            )
            
            grade = llm_output.response["score"]
            if grade == "yes":
                # print("----GRADE: DOCUMENT RELEVANT----")
                logger.info("----GRADE: DOCUMENT RELEVANT----")
                filtered_docs.append(d)
            else:
                # print("----GRADE: DOCUMENT NOT RELEVANT----")
                logger.info("----GRADE: DOCUMENT NOT RELEVANT----")
                continue
        return {**state, "documents": filtered_docs, "question": question}

    def transform_query(self, state: RAGState):
        """
        Transform the query to produce a better question.

        Args:
            state (dict): The current graph state

        Returns:
            state (dict): Updates question key with a re-phrased question
        """
        if self.iteration_count <= 0:
            state['generation'] = "I don't have any additional information about the question."
            state['query_answered'] = False
            return {**state, "next":"update_state"}
        
        if self.max_hallucination == 0:
            state['generation'] = "Model is hallucinating with too many inaccuracies."
            state['query_answered'] = False
            return {**state, "next":"update_state"}
        

        # print("----TRANSFORM QUERY----")
        logger.info("----TRANSFORM QUERY----")
        question = state["question"]
        documents = state["documents"]
        self.iteration_count -= 1

        # Re-write question
        llm_output = self.llm.invoke(self.prompts.re_write_prompt, {"question": question}, 'string')
        return {**state, "documents": documents, "question": llm_output.response, "next":"retrieve"}

    def decide_to_generate(self, state: RAGState):
        """
        Determines whether to generate an answer, or re-generate a question.

        Args:
            state (dict): The current graph state

        Returns:
            str: Binary decision for next node to call
        """

        # print("----ASSESS GRADED DOCUMENTS----")
        logger.info("----ASSESS GRADED DOCUMENTS----")
        question = state["question"]
        filtered_documents = state["documents"]

        if not filtered_documents:
            # All documents have been filtered check_relevance
            # We will re-generate a new query
            # print(
            #     "----DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY----"
            # )
            logger.info("----DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY----")
            return "transform_query"
        else:
            # We have relevant documents, so generate answer
            # print("----DECISION: GENERATE----")
            logger.info("----DECISION: GENERATE----")
            return "generate"

    def grade_generation_v_documents_and_question(self, state: RAGState):
        """
        Determines whether the generation is grounded in the document and answers question.

        Args:
            state (dict): The current graph state

        Returns:
            str: Decision for next node to call
        """

        # print("----CHECK HALLUCINATIONS----")
        logger.info("----CHECK HALLUCINATIONS----")
        question = state["question"]
        documents = state["documents"]
        generation = state["generation"]

        llm_output = self.llm.invoke(self.prompts.halucination_grader_prompt, {
                "documents": documents, 
                "generation": generation
            },
            'json'
        )
        grade = llm_output.response["score"]

        # Check hallucination
        if grade == "yes":
            # print("----DECISION: GENERATION IS GROUNDED IN DOCUMENTS----")
            logger.info("----DECISION: GENERATION IS GROUNDED IN DOCUMENTS----")
            # Check question-answering
            # print("----GRADE GENERATION vs QUESTION----")
            logger.info("----GRADE GENERATION vs QUESTION----")
            llm_output = self.llm.invoke(self.prompts.answer_grader_prompt, {
                    "question": question, 
                    "generation": generation
                },
                'json'
            )
            
            grade = llm_output.response["score"]
            if grade == "yes":
                # print("----DECISION: GENERATION ADDRESSES QUESTION----")
                logger.info("----DECISION: GENERATION ADDRESSES QUESTION----")
                return "useful"
            else:
                # print("----DECISION: GENERATION DOES NOT ADDRESS QUESTION----")
                logger.info("----DECISION: GENERATION DOES NOT ADDRESS QUESTION----")
                return "not useful"
        else:
            # print("----DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY----")
            logger.info("----DECISION: GENERATION DOES NOT ADDRESS QUESTION----")
            self.max_hallucination -= 1
            if self.max_hallucination == 0:
                return "not useful"
            else:
                return "not supported"
    
    def update_state(self, state: RAGState):
        self.state = {**state}
        self.max_hallucination = state['max_hallucination']
        return {**state}
