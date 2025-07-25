"""
Configuration Manager for MCP Integration Layer

This module handles loading and managing MCP server configurations from the
mcp.config.yml file, similar to how RAG agents are configured.
"""

import yaml
import os
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from utils.logger import logger
from core.decorators.singleton import singleton


class MCPTransportType(Enum):
    """Transport types for MCP connections"""
    STDIO = "stdio"
    HTTP = "http"
    WEBSOCKET = "websocket"
    SANDBOX = "sandbox"


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server"""
    name: str
    enabled: bool
    description: str
    transport: MCPTransportType
    # STDIO transport fields
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    # HTTP transport fields
    url: Optional[str] = None
    auth_token: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    # WebSocket transport fields
    ws_url: Optional[str] = None
    # Sandbox transport fields
    e2b_api_key: Optional[str] = None
    sandbox_template_id: Optional[str] = None


@dataclass
class MCPGlobalConfig:
    """Global MCP configuration settings"""
    enabled: bool
    connection_timeout: int
    max_retries: int


@dataclass
class MCPConfig:
    """Complete MCP configuration"""
    global_config: MCPGlobalConfig
    servers: Dict[str, MCPServerConfig]


@singleton
class MCPConfigManager:
    """
    Configuration Manager for MCP Integration Layer
    
    Singleton class that loads and manages MCP server configurations
    from the mcp.servers.genpod.yml file.
    """
    
    def __init__(self):
        self._config: Optional[MCPConfig] = None
        self._config_file_path = self._get_config_file_path()
        self._load_config()
    
    def _get_config_file_path(self) -> Path:
        """Get the path to the MCP configuration file"""
        # Check for environment variable first
        env_path = os.getenv('MCP_CONFIG_PATH')
        if env_path:
            config_path = Path(env_path)
            if not config_path.exists():
                raise FileNotFoundError(f"MCP configuration file not found at environment path: {config_path}")
            return config_path
        
        # Look for config file in the project root
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "mcp.config.yml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"MCP configuration file not found at: {config_path}")
        
        return config_path
    
    async def initialize(self) -> None:
        """Initialize the configuration manager (async interface for consistency)"""
        if self._config is None:
            self._load_config()
        logger.info("MCP Configuration Manager initialized")
    
    def _load_config(self) -> None:
        """Load MCP configuration from YAML file"""
        try:
            logger.info(f"Loading MCP configuration from: {self._config_file_path}")
            
            with open(self._config_file_path, 'r') as file:
                config_data = yaml.safe_load(file)
            
            logger.debug(f"Raw config data loaded: {config_data}")
            
            # Parse global MCP settings
            mcp_global = config_data.get('mcp', {})
            global_config = MCPGlobalConfig(
                enabled=mcp_global.get('enabled', False),
                connection_timeout=mcp_global.get('connection_timeout', 30),
                max_retries=mcp_global.get('max_retries', 3)
            )
            
            logger.info(f"Global MCP config: enabled={global_config.enabled}, timeout={global_config.connection_timeout}s, retries={global_config.max_retries}")
            
            # Parse server configurations
            servers = {}
            servers_data = config_data.get('mcp_servers', {})
            logger.debug(f"Processing {len(servers_data)} server configurations")
            
            for server_name, server_config in servers_data.items():
                logger.debug(f"Processing server config: {server_name}")
                
                try:
                    transport_type = MCPTransportType(server_config.get('transport', 'stdio'))
                    server_obj = MCPServerConfig(
                        name=server_name,
                        enabled=server_config.get('enabled', False),
                        description=server_config.get('description', ''),
                        transport=transport_type,
                        command=server_config.get('command'),
                        args=server_config.get('args'),
                        env=server_config.get('env'),
                        url=server_config.get('url'),
                        auth_token=server_config.get('auth_token'),
                        headers=server_config.get('headers'),
                        ws_url=server_config.get('ws_url'),
                        e2b_api_key=server_config.get('e2b_api_key'),
                        sandbox_template_id=server_config.get('sandbox_template_id')
                    )
                    
                    servers[server_name] = server_obj
                    
                    logger.debug(f"Server {server_name}: enabled={server_obj.enabled}, transport={transport_type.value}")
                    
                except Exception as e:
                    logger.error(f"Failed to parse server config for {server_name}: {e}")
                    raise
            
            # Create complete configuration
            self._config = MCPConfig(
                global_config=global_config,
                servers=servers
            )
            
            enabled_servers = [name for name, config in servers.items() if config.enabled]
            logger.info(f"MCP configuration loaded successfully from {self._config_file_path}")
            logger.info(f"Found {len(servers)} MCP servers configured ({len(enabled_servers)} enabled)")
            
            if enabled_servers:
                logger.info(f"Enabled servers: {', '.join(enabled_servers)}")
            else:
                logger.warning("No MCP servers are enabled")
            
        except Exception as e:
            logger.error(f"Failed to load MCP configuration: {e}", exc_info=True)
            raise
    
    def get_config(self) -> MCPConfig:
        """Get the complete MCP configuration"""
        if self._config is None:
            raise RuntimeError("MCP configuration not loaded")
        return self._config
    
    def get_global_config(self) -> MCPGlobalConfig:
        """Get global MCP configuration"""
        return self.get_config().global_config
    
    def get_server_config(self, server_name: str) -> Optional[MCPServerConfig]:
        """Get configuration for a specific MCP server"""
        return self.get_config().servers.get(server_name)
    
    def get_enabled_servers(self) -> Dict[str, MCPServerConfig]:
        """Get all enabled MCP servers"""
        return {
            name: config for name, config in self.get_config().servers.items()
            if config.enabled
        }
    
    def get_all_enabled_servers(self) -> List[str]:
        """Get list of all enabled server names"""
        return [name for name, config in self.get_enabled_servers().items()]
    
    def is_mcp_enabled(self) -> bool:
        """Check if MCP is globally enabled"""
        return self.get_global_config().enabled
    
    def is_server_enabled(self, server_name: str) -> bool:
        """Check if a specific server is enabled"""
        server_config = self.get_server_config(server_name)
        return server_config.enabled if server_config else False
    
    def reload_config(self) -> None:
        """Reload configuration from file"""
        self._load_config()
        logger.info("MCP configuration reloaded")
    
    def validate_config(self) -> bool:
        """Validate the current configuration"""
        try:
            config = self.get_config()
            
            # Validate global settings
            if not isinstance(config.global_config.connection_timeout, int) or config.global_config.connection_timeout <= 0:
                raise ValueError("Invalid connection_timeout value")
            
            # Validate server configurations
            for server_name, server_config in config.servers.items():
                if server_config.enabled:
                    if server_config.transport == MCPTransportType.STDIO:
                        if not server_config.command:
                            raise ValueError(f"Server {server_name}: command is required for stdio transport")
                        
                        # Validate command exists (basic check)
                        if server_config.command and not server_config.command.startswith('/'):
                            # Try to find command in PATH
                            import shutil
                            if not shutil.which(server_config.command):
                                logger.warning(f"Server {server_name}: command '{server_config.command}' not found in PATH")
                        
                        # Validate args is a list
                        if server_config.args and not isinstance(server_config.args, list):
                            raise ValueError(f"Server {server_name}: args must be a list")
                    
                    elif server_config.transport == MCPTransportType.HTTP:
                        if not server_config.url:
                            raise ValueError(f"Server {server_name}: url is required for http transport")
                        
                        # Basic URL validation
                        if not server_config.url.startswith(('http://', 'https://')):
                            raise ValueError(f"Server {server_name}: url must start with http:// or https://")
                    
                    elif server_config.transport == MCPTransportType.WEBSOCKET:
                        if not server_config.ws_url:
                            raise ValueError(f"Server {server_name}: ws_url is required for websocket transport")
                        
                        # Basic WebSocket URL validation
                        if not server_config.ws_url.startswith(('ws://', 'wss://')):
                            raise ValueError(f"Server {server_name}: ws_url must start with ws:// or wss://")
                    
                    elif server_config.transport == MCPTransportType.SANDBOX:
                        if not server_config.e2b_api_key:
                            raise ValueError(f"Server {server_name}: e2b_api_key is required for sandbox transport")
                        if not server_config.sandbox_template_id:
                            raise ValueError(f"Server {server_name}: sandbox_template_id is required for sandbox transport")
                        
                        # Validate API key format (basic check)
                        if len(server_config.e2b_api_key) < 10:
                            raise ValueError(f"Server {server_name}: e2b_api_key appears to be too short")
                    
                    else:
                        raise ValueError(f"Server {server_name}: unsupported transport type: {server_config.transport}")
            
            # All validation passed
            
            logger.info("MCP configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"MCP configuration validation failed: {e}")
            return False


# Global instance
mcp_config_manager = MCPConfigManager()
