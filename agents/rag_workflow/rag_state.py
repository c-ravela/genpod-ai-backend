""" Graph State for RAG Agent """
from typing import List
from typing_extensions import TypedDict

class RAGState(TypedDict):
    """
    Represents the state of our RAG Retriever.

    Attributes:
        question: question
        generation: LLM generation
        documents: list of documents
    """

    question: str
    generation: str
    documents: List[str]
    iteration_count: int
