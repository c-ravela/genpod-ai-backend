"""
Driving code file for this project.
"""
#  Example using in you main graph.
from langchain_openai import ChatOpenAI
from pprint import pprint
from dotenv import load_dotenv
from agents.supervisor.supervisor_graph import SupervisorWorkflow
from configs.supervisor_config import THREAD_IDS, VECTOR_DB_COLLECTIONS, MEMBERS, RAG_TRY_LIMIT
load_dotenv()

pprint("We greatly appreciate your interest! Please note that we are in the midst of active development and are striving to make improvements every day!")


if __name__=="__main__":
    PROJECT_INPUT = "I want to develop a Title Requests Micro-service adhering to MISMO v3.6 standards to handle get_title service using GET REST API Call in .NET?"
    # PROJECT_INPUT = "How to make money?"
    PROJECT_PATH = "/"
    LICENSE_URL = "https://raw.githubusercontent.com/intelops/tarian-detector/8a4ff75fe31c4ffcef2db077e67a36a067f1437b/LICENSE"
    LICENSE_TEXT = "This code base copyrights belong to XYZ"
    LLM = ChatOpenAI(model="gpt-4o-2024-05-13", temperature=0.2, max_retries=5, streaming=True, seed=4000, top_p=0.8)
    SUPERVISOR_THREAD_ID = "999"
    PROJECT_PATH = '/'
    SUPERVISOR = SupervisorWorkflow(LLM, VECTOR_DB_COLLECTIONS, SUPERVISOR_THREAD_ID, MEMBERS, THREAD_IDS, PROJECT_INPUT, RAG_TRY_LIMIT, PROJECT_PATH)

    config = {"configurable":{"thread_id":SUPERVISOR_THREAD_ID,"recursion_limit":500}}
    result = SUPERVISOR.sup_app.invoke({"messages": [("Human", PROJECT_INPUT)],
                                        'license_url': LICENSE_URL,
                                        'license_text':LICENSE_TEXT},
                                        config)
    pprint(result)
