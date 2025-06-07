"""Main driver for the Genpod project.

This script initializes the tracing session, loads configuration and context,
establishes a database connection, and executes one of several actions based on
command-line input. It supports actions such as project generation, resuming a
project, checking application status, and adding a new project.

Usage:
    python main.py <action> [<additional arguments>]

Actions:
    generate: Generate a new project (requires <project_id> and <user_id>)
    resume: Resume an existing project (requires <user_id>)
    application_status: Check application status (requires <project_id>, <application_id>, <user_id>)
    add_project: Add a new project (requires <user_id>)

Note:
    The tracing session is started and stopped within the main execution block.f"""

import os
import sys

from apis.main import Action
from configs.project_config import ProjectConfig
from configs.project_path import set_project_path
from context.context import GenpodContext
from database.sqlite import SQLite
from utils.logger import logger
from utils.otel import start_trace_session, stop_trace_session, trace_span
from utils.time import get_timestamp
from utils.yaml_utils import read_yaml


@trace_span
def main():
    logger.info("Starting Genpod main execution.")

    if len(sys.argv) < 2:
        logger.error(
            "No action specified. Provide one of: 'generate', 'resume', "
            "'application_status', or 'add_project'."
        )
        sys.exit(1)

    requested_action = sys.argv[1].lower()
    logger.info(f"Action received: {requested_action}")

    setup_config_path = os.getenv("GENPOD_CONFIG")
    if not setup_config_path:
        logger.critical("The environment variable 'GENPOD_CONFIG' is not set.")
        sys.exit(1)
    logger.info(f"Configuration file path retrieved: {setup_config_path}")

    try:
        setup_config = read_yaml(setup_config_path)
        logger.info("Loaded setup configuration successfully.")
    except Exception as e:
        logger.critical(f"Failed to load setup configuration: {e}")
        raise

    db_path = setup_config.get('sqlite3_database_path')
    if not db_path:
        logger.error("Database path missing in configuration.")
        sys.exit(1)
    logger.debug(f"Using SQLite database path: {db_path}")

    try:
        genpod_config_path = setup_config.get('genpod_configuration_file_path')
        if not genpod_config_path:
            logger.warning("Missing 'genpod_configuration_file_path' in setup configuration.")
        config = ProjectConfig(genpod_config_path)
        config.load_config()
        logger.info("Project configuration loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading project configuration: {e}")
        raise

    try:
        genpod_context = GenpodContext()
        logger.info("Initialized Genpod context with default values.")
    except Exception as e:
        logger.error(f"Error initializing Genpod context: {e}", exc_info=True)
        raise

    try:
        db = SQLite(db_path)
        logger.info("Established database connection successfully.")
        db.create_tables()
        logger.info("Database tables created or verified successfully.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

    try:
        action_obj = Action(
            config.agents,
            config.rag_agents,
            db_path,
            config.max_graph_recursion_limit
        )
        logger.debug(f"Initialized Action object: {action_obj}")

        if requested_action == "generate":
            if len(sys.argv) < 4:
                logger.error(
                    "Insufficient arguments for 'generate' action. Expected: <project_id> <user_id>. "
                    "Usage: 'generate <project_id> <user_id>'."
                )
                sys.exit(1)

            project_id = int(sys.argv[2])
            user_id = int(sys.argv[3])
            logger.debug(f"'Generate' action parameters: Project ID = {project_id}, User ID = {user_id}")

            genpod_context.update(project_id=project_id, user_id=user_id)
            project_path = set_project_path(setup_config['code_output_directory'], get_timestamp())
            genpod_context.update(project_path=project_path)
            logger.info(f"Generated project path: {project_path}")
            logger.info("Context updated for 'generate' action.")

            # license_header = "SPDX-License-Identifier: Apache-2.0\nCopyright 2024 Authors of CRBE & the Organization created CRBE"
            license_header = ""
            license_url = "https://raw.githubusercontent.com/intelops/tarian-detector/8a4ff75fe31c4ffcef2db077e67a36a067f1437b/LICENSE"
            action_obj.generate(project_id, user_id, project_path, license_header, license_url)
            logger.info("'Generate' action executed successfully.")

        elif requested_action == "resume":
            if len(sys.argv) < 3:
                logger.error(
                    "Insufficient arguments for 'resume' action. Expected: <user_id>. "
                    "Usage: 'resume <user_id>'."
                )
                sys.exit(1)

            user_id = int(sys.argv[2])
            logger.debug(f"'Resume' action parameter: User ID = {user_id}")

            genpod_context.update(user_id=user_id)
            logger.info("Context updated for the 'resume' action.")

            action_obj.resume(user_id)
            logger.info("The 'resume' action completed successfully.")

        elif requested_action == "application_insights":
            if len(sys.argv) < 5:
                logger.error(
                    "Insufficient arguments for 'application_insights' action. Expected: <project_id> <application_id> <user_id>. "
                    "Usage: 'application_insights <project_id> <application_id> <user_id>'."
                )
                sys.exit(1)

            project_id = int(sys.argv[2])
            application_id = int(sys.argv[3])
            user_id = int(sys.argv[4])
            logger.debug(
                f"'Application Insights' action parameters: Project ID = {project_id}, "
                f"Application ID = {application_id}, User ID = {user_id}"
            )

            genpod_context.update(
                project_id=project_id, application_id=application_id, user_id=user_id
            )
            logger.info("Context updated for the 'application_insights' action.")

            action_obj.application_insights(user_id, project_id, application_id)
            logger.info("The 'application_insights' action completed successfully.")

        elif requested_action == "add_project":
            if len(sys.argv) < 3:
                logger.error(
                    "Insufficient arguments for 'add_project' action. Expected: <user_id>. "
                    "Usage: 'add_project <user_id>'."
                )
                sys.exit(1)

            user_id = int(sys.argv[2])
            logger.debug(f"'Add project' action parameter: User ID = {user_id}")

            genpod_context.update(user_id=user_id)
            logger.info("Context updated for the 'add_project' action.")

            action_obj.add_project(user_id)
            logger.info("The 'add_project' action completed successfully.")
        else:
            logger.error(
                f"Unrecognized action: {requested_action}. Valid actions are 'generate', 'resume', 'application_insights', or 'add_project'."
            )
            sys.exit(1)

    except Exception as e:
        logger.critical(f"An unexpected error occurred while executing action '{requested_action}': {e}", exc_info=True)
        raise
    finally:
        logger.info("Releasing database resources.")
        try:
            db.close_session()
            logger.debug("Database session closed successfully.")
        except Exception as e:
            logger.warning(f"An error occurred while closing the database session: {e}")

        try:
            db.dispose_engine()
            logger.debug("Database engine disposed successfully.")
        except Exception as e:
            logger.warning(f"An error occurred while disposing the database engine: {e}")

        logger.info("All database resources have been released.")

if __name__ == "__main__":
    logger.info("Genpod script execution started.")
    try:
        start_trace_session()
        main()
        stop_trace_session()
        logger.info("Genpod script executed successfully.")
    except Exception as e:
        logger.critical(f"Unhandled exception in script execution: {e}", exc_info=True)
        raise
