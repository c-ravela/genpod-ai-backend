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
        iteration_count: max number of times transform query can happen
    """

    question: str
    generation: str
    documents: List[str]
    iteration_count: int
    next: str
    query_answered: bool
    max_hallucination: int
