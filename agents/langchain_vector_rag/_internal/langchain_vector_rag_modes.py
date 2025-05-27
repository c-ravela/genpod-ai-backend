from enum import Enum


class RAGMode(str, Enum):
    ANSWER_QUERY = "answer_query"
    FINISHED = "finished"

    def __str__(self):
        return self.value


class QueryAnswerStage(str, Enum):
    RETRIEVE_DOCUMENTS = "retrieve_documents"
    GRADE_DOCUMENTS = "grade_documents"
    TRANSFORM_QUERY = "transform_query"
    GENERATE_RESPONSE = "generate_response"
    GRADE_RESPONSE = "grade_response"
    FINISHED = "finished"

    def __str__(self):
        return self.value
