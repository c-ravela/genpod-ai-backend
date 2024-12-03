"""Driving code file for this project."""

import os
import sys
import json
from dotenv import load_dotenv

from configs.project_config import ProjectConfig
from configs.project_path import set_project_path
from database.database import Database
from utils.logs.logging_utils import logger
from utils.time import get_timestamp

from utils.yaml_utils import read_yaml
from apis.project.entity import Project
from apis.main import generate, resume

def main():
    if len(sys.argv) < 2:
        print("ERROR: No action provided. Use 'generate' or 'resume'.")
        sys.exit(1)

    action = sys.argv[1].lower()
    data = sys.argv[2]

    load_dotenv()  # dotenv is just dev environment will be removed for production
    setup_config_path = os.getenv("GENPOD_CONFIG")
    setup_config = read_yaml(setup_config_path)

    db_path = setup_config['sqlite3_database_path']
    db = Database(db_path)
    db.setup_db()

    try:
        genpod_config_path = setup_config['genpod_configuration_file_path']
        config = ProjectConfig(genpod_config_path)
        config.load_config()
        logger.info("Project configuration loaded!")
    except Exception:
        logger.error("Error loading project config.")
        raise

    if action == "generate":
        raw_proj = json.loads(data)
        project_details = Project(
            project_name=raw_proj['project_name'],
            input_prompt="",
            license_text=raw_proj['license_text'],
            license_file_url=raw_proj['license_url'],
            created_by=raw_proj['user_id'],
            project_path=set_project_path(setup_config['code_output_directory'], get_timestamp())
        )
        project_details.id = raw_proj["project_id"]

        generate(
            project_details,
            config.agents,
            config.graphs,
            db_path,
            "MISMO-version-3.6-docs",
            setup_config['vector_database_path'],
            config.max_graph_recursion_limit
        )
    elif action == "resume":
        user_id = int(data)

        resume(
            user_id,
            config.agents,
            config.graphs,
            db_path,
            "MISMO-version-3.6-docs",
            setup_config['vector_database_path'],
            config.max_graph_recursion_limit
        )
    else:
        print(f"❌ Unknown action: {action}. Use 'generate' or 'resume'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
