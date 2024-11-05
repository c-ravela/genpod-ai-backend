"""Driving code file for this project."""

import os

from dotenv import load_dotenv

from agents.supervisor.supervisor_state import SupervisorState
from configs.database import get_client_local_db_file_path
from configs.project_config import ProjectConfig
from configs.project_environment import ProjectEnvironment
from configs.project_path import set_project_path
from database.database import Database
from genpod.team import TeamMembers
from utils.logs.logging_utils import logger
from utils.time import get_timestamp
from utils.fs import read_file

print(
    "\n\nWe greatly appreciate your interest! Please note that we are in the "
    "midst of active development and are striving to make improvements every day!\n\n"
)

if __name__ == "__main__":
    load_dotenv()  # dotenv is just dev environment will be removed for production

    try:
        pe = ProjectEnvironment()

    except Exception:
        logger.error("Error loading environment variables.")
        raise

    try:
        config_path = pe.get_env("GENPOD_CONFIG_PATH")
        config = ProjectConfig(config_path)
        config.load_config()
        logger.info("Project configuration loaded!")
    except Exception:
        logger.error("Error loading project config.")
        raise

    TIME_STAMP = get_timestamp()
    logger.info("Project Generation has been triggered at %s!", TIME_STAMP)

    USER_ID = int(os.getenv("USER_ID"))
    if USER_ID is None:
        raise EnvironmentError(
            "The `USER_ID` environment variable is not set. Please add it to the "
            "'.env' file with the format: USER_ID=4832"
        )

    DATABASE_PATH = get_client_local_db_file_path()
    db = Database(DATABASE_PATH)

    # setup database
    # Tables are created only if they doesn't exist
    db.setup_db()

    PROJECT_INPUT = read_file(config.user_input_path)
    logger.info("Project Input: %s", PROJECT_INPUT)

    LICENSE_URL = (
        "https://raw.githubusercontent.com/intelops/tarian-detector/"
        "8a4ff75fe31c4ffcef2db077e67a36a067f1437b/LICENSE"
    )
    LICENSE_TEXT = (
        "SPDX-License-Identifier: Apache-2.0\nCopyright 2024 Authors of CRBE & the "
        "Organization created CRBE"
    )

    PROJECT_PATH = set_project_path(config.project_output_directory, TIME_STAMP)
    logger.debug("Project is being saved at location: %s", PROJECT_PATH)

    # Database insertion - START
    # insert the record for the project being generated in database
    project_details = db.projects_table.insert(
        "",
        PROJECT_INPUT,
        "",
        PROJECT_PATH,
        USER_ID,
        LICENSE_TEXT,
        LICENSE_URL,
    )
    logger.info(
        f"Records for new project has been created in the database with id: "
        f"{project_details['id']}"
    )

    microservice_details = db.microservices_table.insert(
        "", project_details['id'], "", USER_ID
    )
    logger.info(
        f"Records for new microservice has been created in the database with id: "
        f"{microservice_details['id']}"
    )

    sessions_details = []
    for agent in config.agents:
        session_detail = db.sessions_table.insert(
            project_details['id'], microservice_details['id'], USER_ID
        )
        sessions_details.append(session_detail)

        agent.set_thread_id(session_detail['id'])

    logger.info(
        "Records for new session has been created in the database with ids: "
        f"{', '.join(f'{agent.agent_id}: {agent.thread_id}' for agent in config.agents)}"
    )
    # Database insertion - END

    genpod_team = TeamMembers(
        config.agents, config.graphs, DATABASE_PATH, config.vector_collections_name
    )
    genpod_team.supervisor.set_recursion_limit(config.max_graph_recursion_limit)
    genpod_team.supervisor.graph.agent.setup_team(genpod_team)

    supervisor_response = genpod_team.supervisor.stream(
        {
            "project_id": project_details["id"],
            "microservice_id": microservice_details["id"],
            "original_user_input": PROJECT_INPUT,
            "project_path": PROJECT_PATH,
            "license_url": LICENSE_URL,
            "license_text": LICENSE_TEXT,
        }
    )
    logger.info(
        f"The Genpod team has been notified about the new project. "
        f"{genpod_team.supervisor.member_name} will begin work on it shortly."
    )

    result: SupervisorState = None
    for res in supervisor_response:
        for node_name, super_state in res.items():
            logger.info(
                f"Received state update from supervisor node: {node_name}. "
                f"Response details: {super_state}"
            )
            result = super_state

    # TODO: DB update should happen at for every iteration in the above for loop
    # write a logic to identify changes in the state.
    # NOTE: db doesnt store all the value from the state, it only stores few fields
    # from the state. so, logic should identify the changes to the fields that db stores
    # If there is a change in state then only update the db.
    db.projects_table.update(
        result['project_id'],
        project_name=result['project_name'],
        status=str(result['project_status']),
        updated_by=USER_ID
    )
    db.microservices_table.update(
        result['microservice_id'],
        microservice_name=result['project_name'],
        status=str(result['project_status']),
        updated_by=USER_ID
    )

    print(
        f"Project generated successfully! Project ID: {result['project_id']}, "
        f"Project Name: {result['project_name']}, Location: {PROJECT_PATH}."
    )
    logger.info(
        f"Project generated successfully! Project ID: {result['project_id']}, "
        f"Project Name: {result['project_name']}, Location: {PROJECT_PATH}."
    )
