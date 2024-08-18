""" Graph State for RAG Agent """
from typing import List

from typing_extensions import Annotated, TypedDict

from agents.agent.state import State


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
        State.in_field("query in the form of question for rag to fetch information from vector db.")
    ]

    # @in
    max_hallucination: Annotated[
        int,
        State.in_field("max times of iterations during hallucination")
    ]

    # @out
    generation: Annotated[
        str,
        State.out_field("Information fetch rag for the query")
    ]

    # @inout
    documents: Annotated[
        List[str],
        State.inout_field()
    ]

    # @out
    next: Annotated[
        str,
        State.out_field()
    ]

    # @out
    query_answered: Annotated[
        bool,
        State.out_field(
            "A boolean flag indicating whether the task has been answered"
        )
    ]
