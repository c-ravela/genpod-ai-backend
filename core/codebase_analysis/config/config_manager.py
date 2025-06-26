"""
Configuration management for codebase analysis.

Handles loading and validation of YAML configuration files.
"""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from utils.logger import logger


@dataclass
class AIConfig:
    """Configuration for AI/LLM features."""
    
    enabled: bool = False
    provider: str = "openai"  # openai, azure, claude
    api_key: Optional[str] = None
    model: str = "gpt-4o-mini"
    endpoint: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout: int = 30
    
    # Cost control
    max_requests_per_hour: int = 100
    max_cost_per_day: float = 10.0  # USD
    
    def is_configured(self) -> bool:
        """Check if AI is properly configured."""
        return self.enabled and self.api_key is not None


@dataclass
class StorageConfig:
    """Configuration for storage operations."""
    
    cache_enabled: bool = True
    cache_ttl: int = 3600  # seconds
    max_cache_size: int = 100  # MB
    
    # Storage optimization
    compress_graphs: bool = True
    compress_vectors: bool = False
    auto_cleanup: bool = True
    cleanup_after_days: int = 30


@dataclass
class AnalysisConfig:
    """Configuration for analysis behavior."""
    
    # File processing
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    supported_extensions: List[str] = field(default_factory=lambda: [
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".hpp",
        ".cs", ".rb", ".go", ".rs", ".php", ".swift", ".kt"
    ])
    
    # Analysis depth
    max_dependency_depth: int = 5
    max_call_chain_depth: int = 10
    include_test_files: bool = True
    include_generated_files: bool = False
    
    # Directory exclusions
    exclude_directories: List[str] = field(default_factory=lambda: [
        ".git", ".svn", ".hg",
        "node_modules", "__pycache__", ".pytest_cache",
        "target", "build", "dist", "out",
        ".idea", ".vscode", ".vs"
    ])
    
    # Pattern exclusions
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.min.js", "*.min.css",
        "*.log", "*.tmp", "*.temp",
        "*_pb2.py", "*_pb2_grpc.py"  # Generated protobuf files
    ])
    
    # Processing limits
    max_files_to_process: Optional[int] = None
    parallel_processing: bool = True
    max_workers: int = 4


@dataclass
class GitHooksConfig:
    """Configuration for git hooks integration."""
    
    enabled: bool = False
    auto_install: bool = False
    
    # Which events trigger updates
    on_commit: bool = True
    on_push: bool = False
    on_pull: bool = True
    on_merge: bool = True
    
    # Update behavior
    incremental_updates: bool = True
    async_updates: bool = True
    update_timeout: int = 300  # seconds


@dataclass
class Config:
    """Main configuration class."""
    
    ai: AIConfig = field(default_factory=AIConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    git_hooks: GitHooksConfig = field(default_factory=GitHooksConfig)
    
    # Global settings
    analyzer_type: str = "locagent"
    debug_mode: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        from dataclasses import asdict
        return asdict(self)


class ConfigManager:
    """
    Manages configuration loading, validation, and environment variable overrides.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._config: Optional[Config] = None
    
    def load_config(self, config_path: Optional[str] = None) -> Config:
        """
        Load configuration from YAML file with environment variable overrides.
        
        Args:
            config_path: Path to YAML config file
            
        Returns:
            Loaded and validated configuration
        """
        if config_path:
            self.config_path = config_path
        
        # Start with default config
        config_dict = Config().to_dict()
        
        # Load from file if provided
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config_dict = self._merge_configs(config_dict, file_config)
                        logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load config file {self.config_path}: {e}")
                raise
        
        # Apply environment variable overrides
        config_dict = self._apply_env_overrides(config_dict)
        
        # Create and validate config object
        self._config = self._dict_to_config(config_dict)
        self._validate_config(self._config)
        
        return self._config
    
    def get_config(self) -> Config:
        """Get the current configuration, loading default if not loaded."""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def save_config(self, config: Config, path: str) -> None:
        """Save configuration to YAML file."""
        try:
            config_dict = config.to_dict()
            
            # Remove sensitive information before saving
            if 'ai' in config_dict and 'api_key' in config_dict['ai']:
                config_dict['ai']['api_key'] = '***REDACTED***'
            
            with open(path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                
            logger.info(f"Saved configuration to {path}")
            
        except Exception as e:
            logger.error(f"Failed to save config to {path}: {e}")
            raise
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        
        # AI configuration overrides
        if os.getenv('CODEBASE_AI_ENABLED'):
            config_dict.setdefault('ai', {})['enabled'] = os.getenv('CODEBASE_AI_ENABLED').lower() == 'true'
        
        if os.getenv('OPENAI_API_KEY'):
            config_dict.setdefault('ai', {})['api_key'] = os.getenv('OPENAI_API_KEY')
            config_dict.setdefault('ai', {})['provider'] = 'openai'
        
        if os.getenv('AZURE_OPENAI_API_KEY'):
            config_dict.setdefault('ai', {})['api_key'] = os.getenv('AZURE_OPENAI_API_KEY')
            config_dict.setdefault('ai', {})['provider'] = 'azure'
            if os.getenv('AZURE_OPENAI_ENDPOINT'):
                config_dict['ai']['endpoint'] = os.getenv('AZURE_OPENAI_ENDPOINT')
        
        if os.getenv('ANTHROPIC_API_KEY'):
            config_dict.setdefault('ai', {})['api_key'] = os.getenv('ANTHROPIC_API_KEY')
            config_dict.setdefault('ai', {})['provider'] = 'claude'
        
        # Analysis configuration overrides
        if os.getenv('CODEBASE_MAX_FILES'):
            config_dict.setdefault('analysis', {})['max_files_to_process'] = int(os.getenv('CODEBASE_MAX_FILES'))
        
        if os.getenv('CODEBASE_MAX_WORKERS'):
            config_dict.setdefault('analysis', {})['max_workers'] = int(os.getenv('CODEBASE_MAX_WORKERS'))
        
        # Debug mode
        if os.getenv('CODEBASE_DEBUG'):
            config_dict['debug_mode'] = os.getenv('CODEBASE_DEBUG').lower() == 'true'
        
        return config_dict
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> Config:
        """Convert dictionary to Config object."""
        
        # Extract nested configurations
        ai_config = AIConfig(**config_dict.get('ai', {}))
        storage_config = StorageConfig(**config_dict.get('storage', {}))
        analysis_config = AnalysisConfig(**config_dict.get('analysis', {}))
        git_hooks_config = GitHooksConfig(**config_dict.get('git_hooks', {}))
        
        # Create main config
        return Config(
            ai=ai_config,
            storage=storage_config,
            analysis=analysis_config,
            git_hooks=git_hooks_config,
            analyzer_type=config_dict.get('analyzer_type', 'locagent'),
            debug_mode=config_dict.get('debug_mode', False)
        )
    
    def _validate_config(self, config: Config) -> None:
        """Validate configuration values."""
        
        # Validate AI configuration
        if config.ai.enabled and not config.ai.api_key:
            if config.ai.provider in ['openai', 'azure', 'claude']:
                logger.warning("AI is enabled but no API key is configured")
        
        # Validate analysis limits
        if config.analysis.max_file_size <= 0:
            raise ValueError("Max file size must be positive")
        
        if config.analysis.max_workers <= 0:
            raise ValueError("Max workers must be positive")
        
        # Validate supported analyzer types
        valid_analyzers = ['locagent', 'lsp', 'custom']
        if config.analyzer_type not in valid_analyzers:
            raise ValueError(f"Invalid analyzer type: {config.analyzer_type}. Must be one of {valid_analyzers}")
        
        logger.debug("Configuration validation passed")
    
    @classmethod
    def create_default_config(cls, output_path: str) -> None:
        """Create a default configuration file."""
        default_config = Config()
        
        config_content = """# GenPod Codebase Analysis Configuration

# AI/LLM Configuration
ai:
  enabled: false  # Set to true to enable AI features
  provider: openai  # openai, azure, claude
  api_key: null  # Set your API key or use environment variables
  model: gpt-4o-mini
  endpoint: null  # For Azure or custom endpoints
  max_tokens: 4000
  temperature: 0.1
  timeout: 30
  max_requests_per_hour: 100
  max_cost_per_day: 10.0

# Storage Configuration  
storage:
  cache_enabled: true
  cache_ttl: 3600
  max_cache_size: 100
  compress_graphs: true
  compress_vectors: false
  auto_cleanup: true
  cleanup_after_days: 30

# Analysis Configuration
analysis:
  max_file_size: 10485760  # 10MB
  supported_extensions:
    - .py
    - .js
    - .ts
    - .java
    - .cpp
    - .c
    - .h
    - .hpp
    - .cs
    - .rb
    - .go
    - .rs
    - .php
    - .swift
    - .kt
  max_dependency_depth: 5
  max_call_chain_depth: 10
  include_test_files: true
  include_generated_files: false
  exclude_directories:
    - .git
    - .svn
    - .hg
    - node_modules
    - __pycache__
    - .pytest_cache
    - target
    - build
    - dist
    - out
    - .idea
    - .vscode
    - .vs
  exclude_patterns:
    - "*.min.js"
    - "*.min.css"
    - "*.log"
    - "*.tmp"
    - "*.temp"
    - "*_pb2.py"
    - "*_pb2_grpc.py"
  max_files_to_process: null
  parallel_processing: true
  max_workers: 4

# Git Hooks Configuration
git_hooks:
  enabled: false
  auto_install: false
  on_commit: true
  on_push: false
  on_pull: true
  on_merge: true
  incremental_updates: true
  async_updates: true
  update_timeout: 300

# Global Settings
analyzer_type: locagent
debug_mode: false
"""
        
        with open(output_path, 'w') as f:
            f.write(config_content)
        
        print(f"Created default configuration at {output_path}")
        print("Please edit the configuration file to set your API keys and preferences.")
