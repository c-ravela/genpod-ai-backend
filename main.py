"""Driving code file for this project."""

import os
import sys

from apis.main import Action
from configs.project_config import ProjectConfig
from configs.project_path import set_project_path
from context.context import GenpodContext
from database.sqlite import SQLite
from utils.logs.logging_utils import logger
from utils.time import get_timestamp
from utils.yaml_utils import read_yaml

def main():
    logger.info("Initializing Genpod main execution.")

    if len(sys.argv) < 2:
        logger.error(
            "No action specified. Please provide an action such as 'generate', "
            "'resume', 'microservice_status', or 'add_project'."
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
        logger.info("Successfully loaded setup configuration.")
    except Exception as e:
        logger.critical(f"Failed to load setup configuration. Error: {e}")
        raise

    db_path = setup_config.get('sqlite3_database_path')
    if not db_path:
        logger.error("Database path not found in the configuration.")
        sys.exit(1)
    logger.debug(f"SQLite database path: {db_path}")

    try:
        genpod_config_path = setup_config.get('genpod_configuration_file_path')
        if not genpod_config_path:
            logger.warning(
                "The 'genpod_configuration_file_path' is missing in the setup configuration."
            )
        config = ProjectConfig(genpod_config_path)
        config.load_config()
        logger.info("Project configuration successfully loaded.")
    except Exception as e:
        logger.error(f"Error while loading project configuration: {e}")
        raise

    try:
        genpod_context = GenpodContext()
        logger.info("GenpodContext initialized successfully with default values.")
    except Exception as e:
        logger.error(f"Failed to initialize GenpodContext. Error: {e}", exc_info=True)
        raise

    try:
        db = SQLite(db_path)
        logger.info("Database connection established successfully.")
        db.create_tables()
        logger.info("Database tables created or verified successfully.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        raise

    try:
        action_obj = Action(
            config.agents,
            config.graphs,
            db_path,
            "MISMO-version-3.6-docs",
            setup_config['vector_database_path'],
            config.max_graph_recursion_limit
        )
        logger.debug(f"Action object initialized with configuration: {action_obj}")

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
            logger.info("Context successfully updated for the 'generate' action.")

            action_obj.generate(project_id, user_id, project_path)
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
        elif requested_action == "microservice_status":
            if len(sys.argv) < 5:
                logger.error(
                    "Insufficient arguments for 'microservice_status' action. Expected: <project_id> <service_id> <user_id>. "
                    "Usage: 'microservice_status <project_id> <service_id> <user_id>'."
                )
                sys.exit(1)

            project_id = int(sys.argv[2])
            service_id = int(sys.argv[3])
            user_id = int(sys.argv[4])
            logger.debug(
                f"'Microservice status' action parameters: Project ID = {project_id}, "
                f"Service ID = {service_id}, User ID = {user_id}"
            )

            genpod_context.update(
                project_id=project_id, microservice_id=service_id, user_id=user_id
            )
            logger.info("Context updated for the 'microservice_status' action.")

            action_obj.microservice_status(user_id, project_id, service_id)
            logger.info("The 'microservice_status' action completed successfully.")
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
                f"Unrecognized action: {requested_action}. Valid actions are 'generate', 'resume', 'microservice_status', or 'add_project'."
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
        main()
        logger.info("Genpod script executed successfully.")
    except Exception as e:
        logger.critical(f"Unhandled exception in script execution: {e}", exc_info=True)
        sys.exit(1)
