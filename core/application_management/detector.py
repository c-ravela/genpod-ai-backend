"""
Application Detection Module

Simple utilities for detecting GenPod applications and Git repositories.
Focused on basic detection without complex analysis.
"""

from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass

from utils.logger import logger


@dataclass
class ApplicationInfo:
    """Basic application information"""
    path: str
    is_genpod_application: bool
    is_git_repository: bool
    genpod_path: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "path": self.path,
            "is_genpod_application": self.is_genpod_application,
            "is_git_repository": self.is_git_repository,
            "genpod_path": self.genpod_path
        }


class ApplicationDetector:
    """
    Simple application detector for GenPod applications.
    
    Provides basic detection capabilities:
    - Check if .genpod folder exists
    - Check if Git repository exists
    - Basic application information
    """
    
    @staticmethod
    def detect_application(directory: str) -> ApplicationInfo:
        """
        Detect application type and Git status.
        
        Args:
            directory (str): Path to the directory to analyze
            
        Returns:
            ApplicationInfo: Basic application information
        """
        try:
            dir_path = Path(directory).resolve()
            
            if not dir_path.exists() or not dir_path.is_dir():
                logger.warning(f"Directory does not exist or is not a directory: {directory}")
                return ApplicationInfo(
                    path=str(dir_path),
                    is_genpod_application=False,
                    is_git_repository=False,
                    genpod_path=""
                )
            
            # Check for .genpod folder
            genpod_path = dir_path / ".genpod"
            is_genpod = genpod_path.exists() and genpod_path.is_dir()
            
            # Check for Git repository
            git_path = dir_path / ".git"
            is_git = git_path.exists()
            
            logger.info(f"Detected application at {directory}: GenPod={is_genpod}, Git={is_git}")
            
            return ApplicationInfo(
                path=str(dir_path),
                is_genpod_application=is_genpod,
                is_git_repository=is_git,
                genpod_path=str(genpod_path) if is_genpod else ""
            )
            
        except Exception as e:
            logger.error(f"Failed to detect application at {directory}: {e}")
            return ApplicationInfo(
                path=directory,
                is_genpod_application=False,
                is_git_repository=False,
                genpod_path=""
            )
    
    @staticmethod
    def is_genpod_application(directory: str) -> bool:
        """
        Simple check if directory is a GenPod application.
        
        Args:
            directory (str): Path to the directory
            
        Returns:
            bool: True if .genpod folder exists
        """
        try:
            genpod_path = Path(directory) / ".genpod"
            return genpod_path.exists() and genpod_path.is_dir()
        except Exception as e:
            logger.error(f"Failed to check GenPod application at {directory}: {e}")
            return False
    
    @staticmethod
    def is_git_repository(directory: str) -> bool:
        """
        Simple check if directory is a Git repository.
        
        Args:
            directory (str): Path to the directory
            
        Returns:
            bool: True if .git exists
        """
        try:
            git_path = Path(directory) / ".git"
            return git_path.exists()
        except Exception as e:
            logger.error(f"Failed to check Git repository at {directory}: {e}")
            return False
    
    @staticmethod
    def get_genpod_path(directory: str) -> str:
        """
        Get the .genpod folder path if it exists.
        
        Args:
            directory (str): Path to the directory
            
        Returns:
            str: Path to .genpod folder or empty string if not found
        """
        try:
            genpod_path = Path(directory) / ".genpod"
            if genpod_path.exists() and genpod_path.is_dir():
                return str(genpod_path)
            return ""
        except Exception as e:
            logger.error(f"Failed to get GenPod path at {directory}: {e}")
            return ""


# Convenience functions for easy usage
def quick_detect(directory: str = ".") -> Dict[str, Any]:
    """
    Quick application detection for simple usage.
    
    Args:
        directory (str): Directory to analyze (default: current directory)
        
    Returns:
        Dict[str, Any]: Application information
    """
    info = ApplicationDetector.detect_application(directory)
    return info.to_dict()


def is_genpod_project(directory: str = ".") -> bool:
    """
    Quick check if directory is a GenPod project.
    
    Args:
        directory (str): Directory to check (default: current directory)
        
    Returns:
        bool: True if GenPod project
    """
    return ApplicationDetector.is_genpod_application(directory)