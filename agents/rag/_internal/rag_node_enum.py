from enum import Enum


class RAGNodeEnum(str, Enum):
    ENTRY = "entry"
    RETRIEVE_DOCUMENTS = "retrieve_documents"
    GENERATE_RESPONSE = "generate_response"
    GRADE_DOCUMENTS = "grade_documents"
    TRANSFORM_QUERY = "transform_query"
    GRADE_RESPONSE = "grade_response"
    EXIT = "exit"

    def __str__(self):
        return self.value
