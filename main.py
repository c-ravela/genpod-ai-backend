"""
Driving code file for this project.
"""
import os
from pprint import pprint

from agents.supervisor.supervisor_graph import SupervisorWorkflow
from configs.database import get_client_local_db_file_path
from configs.project_config import ProjectConfig
from configs.project_path import set_project_path
from configs.supervisor_config import RAG_TRY_LIMIT
from database.database import Database
from utils.logs.logging_utils import logger
from utils.time import get_timestamp

print("\n\nWe greatly appreciate your interest! Please note that we are in the midst of active development and are striving to make improvements every day!\n\n")

if __name__=="__main__":
    TIME_STAMP = get_timestamp()
    logger.info(f"Project Generation has been triggered at {TIME_STAMP}!")

    # Initialize the project config
    config = ProjectConfig()
    logger.info("Project configuration loaded!")

    USER_ID = int(os.getenv("USER_ID"))
    if USER_ID is None:
        raise EnvironmentError("The `USER_ID` environment variable is not set. Please add it to the '.env' file with the format: USER_ID=4832")

    DATABASE_PATH = get_client_local_db_file_path()
    db = Database(DATABASE_PATH)

    # setup database
    # Tables are created only if they doesn't exist
    db.setup_db()

    PROJECT_INPUT = """
        Project Overview:
        I want to develop a Title Requests Micro-service adhering to MISMO v3.6 standards to handle get_title service using GET REST API Call in .NET
        Utilize a MongoDB database (using the provided connection details: \"mongodb://localhost:27017/titlerequest\").
        Host the application at "https://crbe.com".
        """
    
    LICENSE_URL = "https://raw.githubusercontent.com/intelops/tarian-detector/8a4ff75fe31c4ffcef2db077e67a36a067f1437b/LICENSE"
    LICENSE_TEXT = """
        SPDX-License-Identifier: Apache-2.0
    Copyright 2024 Authors of CRBE & the Organization created CRBE
    """

    PROJECT_PATH = set_project_path(timestamp=TIME_STAMP)

    # Database insertion - START
    # insert the record for the project being generated in database
    project_details = db.projects_table.insert("", PROJECT_INPUT, PROJECT_PATH, USER_ID, LICENSE_TEXT, LICENSE_URL)
    logger.info(f"Records for new project has been created in the database with id: {project_details['id']}")

    microservice_details = db.microservices_table.insert("", project_details['id'], USER_ID)
    logger.info(f"Records for new microservice has been created in the database with id: {microservice_details['id']}")

    sessions_details = []
    for key, agent in config.agents_config.items():
        session_detail = db.sessions_table.insert(project_details['id'], microservice_details['id'], USER_ID)
        sessions_details.append(session_detail)

        agent.set_thread_id(session_detail['id'])

    logger.info(f"Records for new session has been created in the database with ids: {", ".join(f"{value.agent_id}: {value.thread_id}" for key, value in config.agents_config.items())}")
    # Database insertion - END
    
    supervisor_info = config.agents.supervisor
    SUPERVISOR = SupervisorWorkflow(
        config.agents_config[supervisor_info.agent_id].llm,
        config.vector_db_collections, 
        PROJECT_INPUT, 
        RAG_TRY_LIMIT, 
        PROJECT_PATH, 
        DATABASE_PATH,
        config.agents_config
    )

    sup_config = {"configurable":{"thread_id": config.agents_config[supervisor_info.agent_id].thread_id}, "recursion_limit":500}
    result = SUPERVISOR.workflow.invoke({
        "messages": [("Human", PROJECT_INPUT)],
        'license_url': LICENSE_URL,
        'license_text':LICENSE_TEXT
        }, 
        sup_config
    )
    
    pprint(result)

    # TODO: once state is returned update db with returned value