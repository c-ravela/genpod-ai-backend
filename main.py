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
        logger.error("No action provided. Use 'generate' or 'resume'.")
        print("ERROR: No action provided. Use 'generate' or 'resume'.")
        sys.exit(1)

    action = sys.argv[1].lower()
    data = sys.argv[2]
    logger.info(f"Action received: {action}")

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
        if action == "generate":
            logger.info("Starting 'generate' action.")
            raw_proj = json.loads(data)
            logger.debug(f"Parsed project data: {raw_proj}")

            project = Project(
                id=raw_proj['project_id'],
                project_name=raw_proj['project_name'],
                created_by=raw_proj['user_id']
            )
            logger.info(f"Project object created: {project}")

            new_microservice = Microservice(
                microservice_description="Test microservice",
                project_id=project.id,
                status="NEW",
                license_text=raw_proj['license_text'],
                license_file_url=raw_proj['license_url'],
                project_location=set_project_path(setup_config['code_output_directory'], get_timestamp()),
                created_by=project.created_by,
                updated_by=project.created_by
            )
            logger.info(f"Microservice object created: {new_microservice}")

            Action.generate(
                new_microservice,
                config.agents,
                config.graphs,
                db_path,
                "MISMO-version-3.6-docs",
                setup_config['vector_database_path'],
                config.max_graph_recursion_limit
            )
            logger.info("Generate action completed successfully.")

        elif action == "resume":
            logger.info("Starting 'resume' action.")
            user_id = int(data)
            logger.debug(f"User ID for resume action: {user_id}")

            Action.resume(
                user_id,
                config.agents,
                config.graphs,
                db_path,
                "MISMO-version-3.6-docs",
                setup_config['vector_database_path'],
                config.max_graph_recursion_limit
            )
            logger.info("Resume action completed successfully.")

        else:
            logger.error(f"Unknown action: {action}. Use 'generate' or 'resume'.")
            print(f"❌ Unknown action: {action}. Use 'generate' or 'resume'.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error during '{action}' action execution: {e}")
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
