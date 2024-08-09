""" constants to use in the supervisor agent"""
import os

# thread ids are crucial for graph state persistence so there should be unique for each agent key.
THREAD_IDS = {
    'RAG':'1',
    'Architect':'2',
    'Planner':'3',
    'Coder':'4'
}

# Currently only use this value for collection_name if you have embeded and saved vector into the db with a differnet name then you can use it here.
VECTOR_DB_COLLECTIONS = {'MISMO-version-3.6-docs': os.path.join(os.getcwd(), "vector_collections")}

# Agent Members to use in the setup. Ideal memebers are as below.
MEMBERS = ['RAG', 'Architect', 'Planner', 'Coder', 'Tester', 'Modernizer']
# MEMBERS = ['RAG','Architect','Planner']

# Rag Agent tries to transform the original query for better vector search if failed the first time. This value can be used to set a limit on number of retries.
# 0: Strict Retrieval, will never try to transform the original query
# 1: Recommended, will try to tranform original query once without changing the integrity of the query.
# >1: Not Recommended, can end up running for too long, and cost may blow up.
RAG_TRY_LIMIT = 1

# Map between called agent and node to call by supervisor
calling_map = {
    'RAG':'call_rag',
    'Architect':'call_architect',
    'Planner':'call_planner',
    'Coder':'call_coder'
}
