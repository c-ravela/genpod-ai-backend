from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from agents.base.base_agent import BaseAgent
from agents.rag_workflow.rag_state import RAGState
from apis.rag_analytics.controller import RAGAnalyticsController
from configs.supervisor_config import RAG_TRY_LIMIT
from context.context import GenpodContext
from database.entities.rag_analytics import RAGAnalytics
from llms.llm import LLM
from prompts.rag_prompts import RAGPrompts
from utils.logs.logging_utils import logger


class RAGAgent(BaseAgent[RAGState, RAGPrompts]):
    def __init__(self, agent_id: str, agent_name: str, llm: LLM, collection_name: str, persist_directory: str=None):
        assert persist_directory is not None, "Currently only Local Chroma VectorDB is supported"
        
        super().__init__(
            agent_id,
            agent_name,
            RAGState(),
            RAGPrompts(),
            llm
        )

        self._genpod_context = GenpodContext.get_context()
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
                logger.info("----GRADE: DOCUMENT RELEVANT----")
                filtered_docs.append(d)
            else:
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

        logger.info("----ASSESS GRADED DOCUMENTS----")
        question = state["question"]
        filtered_documents = state["documents"]

        if not filtered_documents:
            # All documents have been filtered check_relevance
            # We will re-generate a new query
            logger.info("----DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY----")
            return "transform_query"
        else:
            # We have relevant documents, so generate answer
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
            logger.info("----DECISION: GENERATION IS GROUNDED IN DOCUMENTS----")
            # Check question-answering
            logger.info("----GRADE GENERATION vs QUESTION----")
            llm_output = self.llm.invoke(self.prompts.answer_grader_prompt, {
                    "question": question, 
                    "generation": generation
                },
                'json'
            )
            
            grade = llm_output.response["score"]
            if grade == "yes":
                logger.info("----DECISION: GENERATION ADDRESSES QUESTION----")
                return "useful"
            else:
                logger.info("----DECISION: GENERATION DOES NOT ADDRESS QUESTION----")
                return "not useful"
        else:
            logger.info("----DECISION: GENERATION DOES NOT ADDRESS QUESTION----")
            self.max_hallucination -= 1
            if self.max_hallucination == 0:
                return "not useful"
            else:
                return "not supported"
    
    def save_analytics_record(self, state: RAGState):
        _analytics_ctrl = RAGAnalyticsController()
        agent_context = self._genpod_context.previous_agent if self._genpod_context.previous_agent else self._genpod_context.current_agent
        _analytics_record = None
        for document in state["documents"]:
            document_id = document.metadata.get('id', "")
            document_version = document.metadata.get('version', "")

            _analytics_record = RAGAnalytics(
                agent_id=agent_context.agent_id,
                project_id=self._genpod_context.project_id,
                microservice_id=self._genpod_context.microservice_id,
                session_id=agent_context.agent_session_id,
                task_id=self._genpod_context.current_task.task_id,

                document_id=document_id,
                document_version=document_version,
                question=state['question'],
                raw_response=document.page_content,
                size_of_data=len(document.page_content),

                created_by=self._genpod_context.user_id,
                updated_by=self._genpod_context.user_id
            )

            _analytics_ctrl.create(_analytics_record)

    def update_state(self, state: RAGState):
        self.state = {**state}
        self.max_hallucination = state['max_hallucination']
        return {**state}
