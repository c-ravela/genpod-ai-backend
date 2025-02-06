""" Graph State for RAG Agent """
from typing import Annotated, List, TypedDict

from agents.base.base_state import BaseState


class RAGState(TypedDict):
    """
    Represents the state of our RAG Retriever.

    Attributes:
        question: question
        generation: LLM generation
        documents: list of documents
        iteration_count: max number of times transform query can happen
    """

    # @in
    question: Annotated[
        str,
        BaseState.in_field("query in the form of question for rag to fetch information from vector db.")
    ]

    # @in
    max_hallucination: Annotated[
        int,
        BaseState.in_field("max times of iterations during hallucination")
    ]

    # @out
    generation: Annotated[
        str,
        BaseState.out_field("Information fetch rag for the query")
    ]

    # @inout
    documents: Annotated[
        List[str],
        BaseState.inout_field()
    ]

    # @out
    next: Annotated[
        str,
        BaseState.out_field()
    ]

    # @out
    query_answered: Annotated[
        bool,
        BaseState.out_field(
            "A boolean flag indicating whether the task has been answered"
        )
    ]
