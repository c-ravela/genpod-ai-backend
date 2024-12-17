"""Driving code file for this project."""

import json
import os
import sys

from dotenv import load_dotenv

from apis.main import Action
from configs.project_config import ProjectConfig
from configs.project_path import set_project_path
from database.entities.microservices import Microservice
from database.entities.projects import Project
from database.sqlite import SQLite
from utils.logs.logging_utils import logger
from utils.time import get_timestamp
from utils.yaml_utils import read_yaml


def main():
    logger.info("Starting main genpod execution.")

    if len(sys.argv) < 2:
        logger.error("No action provided. Use 'generate', 'resume', 'microservice_status', or 'add_project'.")
        print("ERROR: No action provided. Use 'generate', 'resume', 'microservice_status', or 'add_project'.")
        sys.exit(1)

    requested_action = sys.argv[1].lower()
    logger.info(f"Action received: {requested_action}")

    load_dotenv()  # dotenv is just dev environment will be removed for production
    setup_config_path = os.getenv("GENPOD_CONFIG")
    logger.info(f"Loading setup configuration from: {setup_config_path}")

    try:
        setup_config = read_yaml(setup_config_path)
        logger.info("Setup configuration loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load setup configuration: {e}")
        raise

    db_path = setup_config['sqlite3_database_path']
    logger.info(f"Using SQLite database path: {db_path}")

    try:
        genpod_config_path = setup_config['genpod_configuration_file_path']
        config = ProjectConfig(genpod_config_path)
        config.load_config()
        logger.info("Project configuration loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading project configuration: {e}")
        raise
    
    try:
        db = SQLite(db_path)
        logger.info("Database initialized successfully.")
        db.create_tables()
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
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

        if requested_action == "generate":
            if len(sys.argv) < 4:
                logger.error("ERROR: 'generate' requires <project_id> <user_id>. Usage: 'generate <project_id> <user_id>'")
                print("ERROR: 'generate' requires <project_id> <user_id>. Usage: 'generate <project_id> <user_id>'")
                sys.exit(1)
            project_id = int(sys.argv[2])
            user_id = int(sys.argv[3])
        
            logger.info("Starting 'generate' action.")

            project_path = set_project_path(setup_config['code_output_directory'], get_timestamp())
            action_obj.generate(project_id, user_id, project_path)
            logger.info("Generate action completed successfully.")
        elif requested_action == "resume":
            if len(sys.argv) < 3:
                logger.error("ERROR: 'resume' requires <user_id>. Usage: 'resume <user_id>'")
                sys.exit(1)
            user_id = int(sys.argv[2])
            logger.info("Starting 'resume' action.")
            logger.debug(f"User ID for resume action: {user_id}")

            action_obj.resume(user_id)
            logger.info("Resume action completed successfully.")
        elif requested_action == "microservice_status":
            if len(sys.argv) < 5:
                print("ERROR: 'microservice_status' requires <project_id> <service_id> <user_id>. Usage: 'microservice_status <project_id> <service_id> <user_id>'")
                sys.exit(1)
            project_id = int(sys.argv[2])
            service_id = int(sys.argv[3])
            user_id = int(sys.argv[4])

            logger.info("Starting 'microservice_status' action.")
            logger.debug(f"Microservice ID for microservice_status action: {service_id}")

            action_obj.microservice_status(user_id, project_id, service_id)
            logger.info("Microservice status action completed successfully.")
        elif requested_action == "add_project":
            if len(sys.argv) < 3:
                print("ERROR: 'add_project' requires <user_id>. Usage: 'add_project <user_id>'")
                sys.exit(1)
            user_id = int(sys.argv[2])

            logger.info("Starting 'add_project' action.")
            logger.debug(f"User ID for add_project action: {user_id}")

            action_obj.add_project(user_id)
            logger.info("Add project action completed successfully.")
        else:
            logger.error(f"Unknown action: {requested_action}. Use 'generate' or 'resume'.")
            print(f"❌ Unknown action: {requested_action}. Use 'generate' or 'resume'.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error during '{requested_action}' action execution: {e}")
        raise
    finally:
        logger.info("Closing database session and disposing engine.")
        db.close_session()
        db.dispose_engine()
        logger.info("Database resources released successfully.")
    
if __name__ == "__main__":
    logger.info("Script execution started.")
    try:
        main()
        logger.info("Script execution completed successfully.")
    except Exception as e:
        logger.critical(f"Unhandled exception in main execution: {e}", exc_info=True)
        sys.exit(1)
