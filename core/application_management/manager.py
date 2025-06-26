"""
Application Management Module

Handles basic .genpod folder creation and session tracking integration.
Simplified version focused on essential functionality.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from database.database import Database
from database.entities.applications import Application
from database.entities.application_sessions import ApplicationSession
from utils.logger import logger


class ApplicationManager:
    """
    Manages GenPod application setup and session tracking.
    
    Provides simplified functionality:
    - Create .genpod folder structure
    - Database integration for applications and sessions
    - Basic session tracking
    """
    
    def __init__(self, application_path: str):
        """
        Initialize ApplicationManager.
        
        Args:
            application_path (str): Root directory of the application
        """
        self.application_path = Path(application_path).resolve()
        self.genpod_path = self.application_path / ".genpod"
        
        logger.info(f"Initialized ApplicationManager for: {self.application_path}")
    
    def ensure_genpod_structure(self) -> bool:
        """
        Create basic .genpod folder structure if it doesn't exist.
        Note: code_analysis/ directory is automatically created by codebase_analysis module.
        
        Returns:
            bool: True if successful
        """
        try:
            # Create main .genpod directory
            self.genpod_path.mkdir(exist_ok=True)
            
            # Create only application-specific subdirectories
            # Note: code_analysis/ is created automatically by codebase_analysis module
            essential_dirs = [
                "sessions",       # For session data
                "config"          # For application config
            ]
            
            for subdir in essential_dirs:
                (self.genpod_path / subdir).mkdir(exist_ok=True)
            
            # Create basic .gitignore for .genpod folder
            gitignore_content = """# GenPod application metadata
*.tmp
*.log
sessions/*.json
code_analysis/cache/
"""
            gitignore_path = self.genpod_path / ".gitignore"
            if not gitignore_path.exists():
                gitignore_path.write_text(gitignore_content)
            
            logger.info(f"Ensured .genpod structure at: {self.genpod_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create .genpod structure: {e}")
            return False
    
    def get_or_create_application_record(
        self,
        application_name: str,
        project_id: int,
        user_id: int,
        description: str = "",
        prompt: str = ""
    ) -> Optional[int]:
        """
        Get existing application record or create new one.
        
        Args:
            application_name (str): Name of the application
            project_id (int): Project ID from database
            user_id (int): User ID
            description (str): Application description
            prompt (str): Initial prompt/requirements
            
        Returns:
            Optional[int]: Application ID or None if failed
        """
        try:
            db_session = Database.get_db_session()
            
            # Check if application already exists for this location
            existing_app = db_session.query(Application).filter(
                Application.project_location == str(self.application_path),
                Application.project_id == project_id
            ).first()
            
            if existing_app:
                logger.info(f"Found existing application record: {existing_app.id}")
                return existing_app.id
            
            # Create new application record
            new_app = Application(
                application_name=application_name,
                application_description=description,
                prompt=prompt,
                project_id=project_id,
                status="active",
                project_location=str(self.application_path),
                created_by=user_id,
                updated_by=user_id
            )
            
            db_session.add(new_app)
            db_session.commit()
            
            logger.info(f"Created new application record: {new_app.id}")
            return new_app.id
            
        except Exception as e:
            logger.error(f"Failed to get/create application record: {e}")
            if 'db_session' in locals():
                db_session.rollback()
            return None
    
    def start_session(
        self,
        agent_id: str,
        project_id: int,
        application_id: int,
        user_id: int,
        session_description: str = ""
    ) -> Optional[int]:
        """
        Start a new application session.
        
        Args:
            agent_id (str): Agent identifier (e.g., "code_editor", "coder", "tester")
            project_id (int): Project ID
            application_id (int): Application ID
            user_id (int): User ID
            session_description (str): Description of what this session will do
            
        Returns:
            Optional[int]: Session ID or None if failed
        """
        try:
            db_session = Database.get_db_session()
            
            session = ApplicationSession(
                agent_id=agent_id,
                project_id=project_id,
                application_id=application_id,
                created_by=user_id,
                updated_by=user_id
            )
            
            db_session.add(session)
            db_session.commit()
            
            # Store session info locally for quick access
            session_info = {
                "session_id": session.id,
                "agent_id": agent_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "description": session_description,
                "status": "active"
            }
            
            self._save_session_info(session.id, session_info)
            
            logger.info(f"Started session {session.id} for agent {agent_id}")
            return session.id
            
        except Exception as e:
            logger.error(f"Failed to start session: {e}")
            if 'db_session' in locals():
                db_session.rollback()
            return None
    
    def end_session(
        self,
        session_id: int,
        files_modified: list = None,
        session_summary: str = ""
    ) -> bool:
        """
        End an application session and update records.
        
        Args:
            session_id (int): Session ID
            files_modified (list): List of files that were modified
            session_summary (str): Summary of what was accomplished
            
        Returns:
            bool: True if successful
        """
        try:
            # Update local session info
            session_info = self._load_session_info(session_id)
            if session_info:
                session_info.update({
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                    "status": "completed",
                    "files_modified": files_modified or [],
                    "summary": session_summary
                })
                self._save_session_info(session_id, session_info)
            
            logger.info(f"Ended session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return False
    
    def get_application_info(self) -> Dict[str, Any]:
        """
        Get basic information about the application.
        
        Returns:
            Dict[str, Any]: Application information
        """
        try:
            return {
                "application_path": str(self.application_path),
                "genpod_path": str(self.genpod_path),
                "has_genpod_structure": self.genpod_path.exists(),
                "code_analysis_path": str(self.genpod_path / "code_analysis"),
                "sessions_path": str(self.genpod_path / "sessions")
            }
        except Exception as e:
            logger.error(f"Failed to get application info: {e}")
            return {}
    
    def _save_session_info(self, session_id: int, session_info: Dict[str, Any]) -> None:
        """Save session info to local file for quick access."""
        try:
            sessions_dir = self.genpod_path / "sessions"
            sessions_dir.mkdir(exist_ok=True)
            
            session_file = sessions_dir / f"session_{session_id}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_info, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save session info for {session_id}: {e}")
    
    def _load_session_info(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Load session info from local file."""
        try:
            session_file = self.genpod_path / "sessions" / f"session_{session_id}.json"
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
            
        except Exception as e:
            logger.error(f"Failed to load session info for {session_id}: {e}")
            return None


# Convenience functions
def setup_genpod_application(
    application_path: str,
    application_name: str,
    project_id: int,
    user_id: int
) -> Optional[ApplicationManager]:
    """
    Setup a GenPod application with all necessary structure.
    
    Args:
        application_path (str): Path to the application
        application_name (str): Name of the application
        project_id (int): Project ID
        user_id (int): User ID
        
    Returns:
        Optional[ApplicationManager]: Manager instance or None if failed
    """
    try:
        manager = ApplicationManager(application_path)
        
        # Ensure .genpod structure exists
        if not manager.ensure_genpod_structure():
            logger.error("Failed to create .genpod structure")
            return None
        
        # Create/get application record
        app_id = manager.get_or_create_application_record(
            application_name=application_name,
            project_id=project_id,
            user_id=user_id
        )
        
        if not app_id:
            logger.error("Failed to create application record")
            return None
        
        logger.info(f"Successfully setup GenPod application: {application_name}")
        return manager
        
    except Exception as e:
        logger.error(f"Failed to setup GenPod application: {e}")
        return None