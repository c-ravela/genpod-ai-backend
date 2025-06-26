"""
Git hooks integration for automatic context updates.

Provides utilities for installing and managing git hooks that automatically
update codebase context when code changes.
"""

import os
import stat
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from utils.logger import logger


class GitHooksManager:
    """
    Manages git hooks for automatic codebase analysis updates.
    
    Installs and manages hooks that trigger context updates when
    code changes through git operations.
    """
    
    def __init__(self, repository_path: str, analysis_config: Dict[str, Any]):
        self.repo_path = Path(repository_path)
        self.analysis_config = analysis_config
        self.logger = logger
        
        self.git_dir = self.repo_path / ".git"
        self.hooks_dir = self.git_dir / "hooks"
        
        # Check if we're in a git repository
        if not self.git_dir.exists():
            raise ValueError(f"Not a git repository: {repository_path}")
    
    def install_hooks(self, 
                     hooks_config: Dict[str, Any],
                     storage_base_path: str,
                     config_path: Optional[str] = None) -> bool:
        """
        Install git hooks for automatic context updates.
        
        Args:
            hooks_config: Configuration for hooks behavior
            storage_base_path: Path to .genpod storage directory
            config_path: Optional path to analysis configuration
            
        Returns:
            True if hooks were installed successfully
        """
        try:
            self.logger.info(f"Installing git hooks in {self.repo_path}")
            
            # Ensure hooks directory exists
            self.hooks_dir.mkdir(exist_ok=True)
            
            # Install requested hooks
            hooks_installed = []
            
            if hooks_config.get('on_commit', True):
                if self._install_hook('post-commit', storage_base_path, config_path):
                    hooks_installed.append('post-commit')
            
            if hooks_config.get('on_push', False):
                if self._install_hook('pre-push', storage_base_path, config_path):
                    hooks_installed.append('pre-push')
            
            if hooks_config.get('on_pull', True):
                if self._install_hook('post-merge', storage_base_path, config_path):
                    hooks_installed.append('post-merge')
            
            if hooks_config.get('on_merge', True):
                # post-merge hook handles both pull and merge
                pass
            
            if hooks_installed:
                self.logger.info(f"Successfully installed hooks: {', '.join(hooks_installed)}")
                return True
            else:
                self.logger.warning("No hooks were installed")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to install git hooks: {e}")
            return False
    
    def uninstall_hooks(self) -> bool:
        """
        Uninstall codebase analysis git hooks.
        
        Returns:
            True if hooks were uninstalled successfully
        """
        try:
            hook_names = ['post-commit', 'pre-push', 'post-merge']
            uninstalled = []
            
            for hook_name in hook_names:
                hook_file = self.hooks_dir / hook_name
                if hook_file.exists():
                    # Check if it's our hook
                    with open(hook_file, 'r') as f:
                        content = f.read()
                    
                    if 'GENPOD_CODEBASE_ANALYSIS' in content:
                        hook_file.unlink()
                        uninstalled.append(hook_name)
            
            if uninstalled:
                self.logger.info(f"Uninstalled hooks: {', '.join(uninstalled)}")
            else:
                self.logger.info("No hooks to uninstall")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to uninstall git hooks: {e}")
            return False
    
    def check_hooks_status(self) -> Dict[str, bool]:
        """
        Check which hooks are currently installed.
        
        Returns:
            Dictionary mapping hook names to installation status
        """
        status = {}
        hook_names = ['post-commit', 'pre-push', 'post-merge']
        
        for hook_name in hook_names:
            hook_file = self.hooks_dir / hook_name
            
            if hook_file.exists():
                try:
                    with open(hook_file, 'r') as f:
                        content = f.read()
                    status[hook_name] = 'GENPOD_CODEBASE_ANALYSIS' in content
                except Exception:
                    status[hook_name] = False
            else:
                status[hook_name] = False
        
        return status
    
    def _install_hook(self, 
                     hook_name: str, 
                     storage_base_path: str,
                     config_path: Optional[str] = None) -> bool:
        """Install a specific git hook."""
        try:
            hook_file = self.hooks_dir / hook_name
            
            # Generate hook script
            hook_script = self._generate_hook_script(
                hook_name, 
                storage_base_path, 
                config_path
            )
            
            # Handle existing hooks
            if hook_file.exists():
                # Check if it's already our hook
                with open(hook_file, 'r') as f:
                    existing_content = f.read()
                
                if 'GENPOD_CODEBASE_ANALYSIS' in existing_content:
                    self.logger.info(f"Hook {hook_name} already installed")
                    return True
                else:
                    # Backup existing hook
                    backup_file = hook_file.with_suffix('.backup')
                    hook_file.rename(backup_file)
                    self.logger.info(f"Backed up existing {hook_name} to {backup_file}")
            
            # Write new hook
            with open(hook_file, 'w') as f:
                f.write(hook_script)
            
            # Make executable
            hook_file.chmod(hook_file.stat().st_mode | stat.S_IEXEC)
            
            self.logger.debug(f"Installed {hook_name} hook")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to install {hook_name} hook: {e}")
            return False
    
    def _generate_hook_script(self, 
                             hook_name: str, 
                             storage_base_path: str,
                             config_path: Optional[str] = None) -> str:
        """Generate the git hook script content."""
        
        # Determine Python executable
        python_exe = "python3"  # Could be made configurable
        
        # Build command
        repo_path = str(self.repo_path)
        
        cmd_parts = [
            python_exe,
            "-c",
            f"\"from core.codebase_analysis import CodebaseAnalysisFactory; "
            f"analyzer = CodebaseAnalysisFactory.create('{storage_base_path}'"
        ]
        
        if config_path:
            cmd_parts[-1] += f", config_path='{config_path}'"
        
        cmd_parts[-1] += f"); analyzer.update_context('{repo_path}')\""
        
        # Generate script
        script = f"""#!/bin/bash
# GENPOD_CODEBASE_ANALYSIS - Auto-generated git hook
# This hook automatically updates codebase analysis context

# Configuration
REPO_PATH="{repo_path}"
STORAGE_PATH="{storage_base_path}"
CONFIG_PATH="{config_path or ''}"

# Logging
HOOK_LOG="{storage_base_path}/hooks.log"

echo "$(date): {hook_name} hook triggered" >> "$HOOK_LOG"

# Check if analysis is enabled
if [ ! -d "$STORAGE_PATH" ]; then
    echo "$(date): Codebase analysis not initialized, skipping update" >> "$HOOK_LOG"
    exit 0
fi

# Run analysis update in background to avoid blocking git operations
{{
    echo "$(date): Starting context update..." >> "$HOOK_LOG"
    
    # Change to repository directory
    cd "$REPO_PATH"
    
    # Run the update
    {' '.join(cmd_parts)} 2>&1 >> "$HOOK_LOG"
    
    if [ $? -eq 0 ]; then
        echo "$(date): Context update completed successfully" >> "$HOOK_LOG"
    else
        echo "$(date): Context update failed" >> "$HOOK_LOG"
    fi
}} &

# Don't wait for completion to avoid blocking git
exit 0
"""
        
        return script
    
    def test_hook(self, hook_name: str) -> bool:
        """
        Test if a specific hook works correctly.
        
        Args:
            hook_name: Name of the hook to test
            
        Returns:
            True if hook executed successfully
        """
        try:
            hook_file = self.hooks_dir / hook_name
            
            if not hook_file.exists():
                self.logger.error(f"Hook {hook_name} not found")
                return False
            
            # Test execution
            result = subprocess.run(
                [str(hook_file)],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info(f"Hook {hook_name} test passed")
                return True
            else:
                self.logger.error(f"Hook {hook_name} test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Hook {hook_name} test timed out")
            return False
        except Exception as e:
            self.logger.error(f"Hook {hook_name} test error: {e}")
            return False
    
    def get_hook_logs(self, lines: int = 50) -> List[str]:
        """
        Get recent entries from hook logs.
        
        Args:
            lines: Number of recent lines to return
            
        Returns:
            List of log lines
        """
        try:
            log_file = Path(self.analysis_config.get('storage', {}).get('base_path', '.genpod')) / "hooks.log"
            
            if not log_file.exists():
                return []
            
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
            
            return [line.strip() for line in all_lines[-lines:]]
            
        except Exception as e:
            self.logger.error(f"Failed to read hook logs: {e}")
            return []
    
    @staticmethod
    def is_git_repository(path: str) -> bool:
        """Check if path is a git repository."""
        return (Path(path) / ".git").exists()
    
    @staticmethod
    def get_git_info(repo_path: str) -> Dict[str, Any]:
        """Get git repository information."""
        try:
            repo_path = Path(repo_path)
            
            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(repo_path),
                capture_output=True,
                text=True
            )
            current_branch = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            # Get latest commit
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_path),
                capture_output=True,
                text=True
            )
            latest_commit = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            return {
                "current_branch": current_branch,
                "latest_commit": latest_commit,
                "repo_path": str(repo_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get git info: {e}")
            return {
                "current_branch": "unknown",
                "latest_commit": "unknown",
                "repo_path": str(repo_path)
            }
