"""
Connection Manager for MCP Integration Layer

This module manages MCP server connections using the mcp-use package.
It provides a high-level interface for connecting to, managing, and monitoring
MCP servers while handling connection lifecycle and error recovery.
"""

import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import time

from mcp_use import MCPClient, MCPSession
from utils.logger import logger
from core.decorators.singleton import singleton
from core.mcp.config_manager import mcp_config_manager, MCPServerConfig, MCPTransportType


class ConnectionStatus(Enum):
    """Connection status for MCP servers"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class ConnectionInfo:
    """Information about a MCP server connection"""
    server_name: str
    status: ConnectionStatus
    session: Optional[MCPSession] = None
    last_connected: Optional[float] = None
    last_error: Optional[str] = None
    retry_count: int = 0
    config: Optional[MCPServerConfig] = None
    lock: Optional[asyncio.Lock] = None
    
    def __post_init__(self):
        """Initialize the asyncio lock after object creation"""
        if self.lock is None:
            self.lock = asyncio.Lock()


@singleton
class MCPConnectionManager:
    """
    Connection Manager for MCP Integration Layer
    
    Singleton class that manages connections to MCP servers using mcp-use package.
    Handles connection lifecycle, health monitoring, and error recovery.
    """
    
    def __init__(self):
        self._connections: Dict[str, ConnectionInfo] = {}
        self._mcp_client: Optional[MCPClient] = None
        self._initialized = False
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """Initialize the connection manager"""
        if self._initialized:
            return
            
        try:
            # Get MCP configuration
            config = mcp_config_manager.get_config()
            
            if not config.global_config.enabled:
                logger.info("MCP is disabled, skipping connection manager initialization")
                return
            
            # Create MCPClient instance
            self._mcp_client = MCPClient()
            
            # Initialize connection info for all configured servers
            for server_name, server_config in config.servers.items():
                self._connections[server_name] = ConnectionInfo(
                    server_name=server_name,
                    status=ConnectionStatus.DISCONNECTED,
                    config=server_config
                )
            
            self._initialized = True
            logger.info("MCP Connection Manager initialized with %d servers", len(self._connections))
            
        except Exception as e:
            logger.error("Failed to initialize MCP Connection Manager: %s", e, exc_info=True)
            raise
    
    async def connect_to_server(self, server_name: str) -> bool:
        """
        Connect to a specific MCP server
        
        Args:
            server_name: Name of the server to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        if not self._initialized:
            logger.debug("Connection manager not initialized, initializing now...")
            await self.initialize()
            
        if server_name not in self._connections:
            logger.error(f"Unknown MCP server: {server_name}")
            return False
            
        async with self._lock:
            connection_info = self._connections[server_name]
            
            # Check if already connected
            if connection_info.status == ConnectionStatus.CONNECTED:
                logger.debug(f"Already connected to MCP server: {server_name}")
                return True
            
            # Check if server is enabled
            if not connection_info.config.enabled:
                logger.debug(f"Warning: MCP server {server_name} is disabled, skipping connection")
                return False
            
            try:
                connection_info.status = ConnectionStatus.CONNECTING
                logger.info(f"Connecting to MCP server: {server_name}")
                logger.debug(f"Server config: transport={connection_info.config.transport.value}")
                
                # Get connection timeout from config
                global_config = mcp_config_manager.get_global_config()
                timeout = global_config.connection_timeout
                logger.debug(f"Connection timeout: {timeout}s")
                
                # Add server to MCPClient based on transport type with timeout
                logger.debug(f"Adding server {server_name} to MCP client...")
                await asyncio.wait_for(
                    self._add_server_to_client(server_name, connection_info.config),
                    timeout=timeout
                )
                
                # Create session with timeout
                logger.debug(f"Creating session for server {server_name}...")
                session = await asyncio.wait_for(
                    self._mcp_client.create_session(server_name),
                    timeout=timeout
                )
                
                # Update connection info
                connection_info.session = session
                connection_info.status = ConnectionStatus.CONNECTED
                connection_info.last_connected = time.time()
                connection_info.last_error = None
                connection_info.retry_count = 0
                
                logger.info(f"Successfully connected to MCP server: {server_name}")
                return True
                
            except asyncio.TimeoutError:
                error_msg = f"Connection to MCP server {server_name} timed out after {timeout}s"
                logger.error(f"Timeout: {error_msg}")
                
                connection_info.status = ConnectionStatus.ERROR
                connection_info.last_error = error_msg
                connection_info.retry_count += 1
                
                return False
                
            except Exception as e:
                error_msg = f"Failed to connect to MCP server {server_name}: {e}"
                logger.error(f"Failed to connect: {error_msg}", exc_info=True)
                
                connection_info.status = ConnectionStatus.ERROR
                connection_info.last_error = str(e)
                connection_info.retry_count += 1
                
                return False
    
    async def _add_server_to_client(self, server_name: str, config: MCPServerConfig) -> None:
        """Add server configuration to MCPClient"""
        server_config = {}
        
        if config.transport == MCPTransportType.STDIO:
            server_config = {
                "command": config.command,
                "args": config.args or [],
                "env": config.env or {}
            }
        elif config.transport == MCPTransportType.HTTP:
            server_config = {
                "url": config.url
            }
            if config.auth_token:
                server_config["auth_token"] = config.auth_token
            if config.headers:
                server_config["headers"] = config.headers
        elif config.transport == MCPTransportType.WEBSOCKET:
            server_config = {
                "ws_url": config.ws_url
            }
            if config.auth_token:
                server_config["auth_token"] = config.auth_token
        elif config.transport == MCPTransportType.SANDBOX:
            server_config = {
                "command": config.command,
                "args": config.args or [],
                "env": config.env or {}
            }
            if config.e2b_api_key:
                server_config["e2b_api_key"] = config.e2b_api_key
            if config.sandbox_template_id:
                server_config["sandbox_template_id"] = config.sandbox_template_id
        
        # Add server to MCPClient
        self._mcp_client.add_server(server_name, server_config)
        logger.debug("Added server %s to MCPClient with config: %s", server_name, server_config)
    
    async def disconnect_from_server(self, server_name: str) -> None:
        """Disconnect from a specific MCP server"""
        if server_name not in self._connections:
            logger.warning("Cannot disconnect from unknown server: %s", server_name)
            return
            
        async with self._lock:
            connection_info = self._connections[server_name]
            
            if connection_info.status == ConnectionStatus.DISCONNECTED:
                logger.debug("Already disconnected from server: %s", server_name)
                return
            
            try:
                # Close session if it exists
                if connection_info.session:
                    await connection_info.session.close()
                
                # Update connection info
                connection_info.session = None
                connection_info.status = ConnectionStatus.DISCONNECTED
                connection_info.last_error = None
                
                logger.info("Disconnected from MCP server: %s", server_name)
                
            except Exception as e:
                logger.error("Error disconnecting from server %s: %s", server_name, e, exc_info=True)
    
    async def get_connection(self, server_name: str) -> Optional[MCPSession]:
        """
        Get connection session for a specific server
        
        Args:
            server_name: Name of the server
            
        Returns:
            MCPSession if connected, None otherwise
        """
        if server_name not in self._connections:
            logger.warning("Unknown MCP server: %s", server_name)
            return None
            
        connection_info = self._connections[server_name]
        
        # Use connection-specific lock to prevent race conditions
        async with connection_info.lock:
            # Auto-connect if not connected
            if connection_info.status == ConnectionStatus.DISCONNECTED:
                await self.connect_to_server(server_name)
                
            if connection_info.status == ConnectionStatus.CONNECTED:
                return connection_info.session
                
            return None
    
    def is_connected(self, server_name: str) -> bool:
        """Check if a server is connected"""
        if server_name not in self._connections:
            return False
            
        return self._connections[server_name].status == ConnectionStatus.CONNECTED
    
    def get_connection_status(self, server_name: str) -> Optional[ConnectionStatus]:
        """Get connection status for a server"""
        if server_name not in self._connections:
            return None
            
        return self._connections[server_name].status
    
    async def reconnect_to_server(self, server_name: str) -> bool:
        """Reconnect to a specific server"""
        if server_name not in self._connections:
            logger.warning("Cannot reconnect to unknown server: %s", server_name)
            return False
            
        connection_info = self._connections[server_name]
        
        # Check retry limits
        config = mcp_config_manager.get_global_config()
        if connection_info.retry_count >= config.max_retries:
            logger.warning("Max retries exceeded for server %s", server_name)
            return False
            
        # Disconnect first
        await self.disconnect_from_server(server_name)
        
        # Wait before reconnecting with exponential backoff
        backoff_delay = min(2 ** connection_info.retry_count, 30)  # Cap at 30 seconds
        await asyncio.sleep(backoff_delay)
        
        # Reconnect
        connection_info.status = ConnectionStatus.RECONNECTING
        return await self.connect_to_server(server_name)
    
    async def connect_to_all_enabled_servers(self) -> Dict[str, bool]:
        """Connect to all enabled MCP servers"""
        if not self._initialized:
            logger.debug("Connection manager not initialized, initializing now...")
            await self.initialize()
            
        enabled_servers = mcp_config_manager.get_enabled_servers()
        results = {}
        
        logger.info(f"Connecting to {len(enabled_servers)} enabled MCP servers...")
        
        # Connect to all enabled servers concurrently
        tasks = []
        server_names = list(enabled_servers.keys())
        
        for server_name in server_names:
            logger.debug(f"Creating connection task for server: {server_name}")
            task = asyncio.create_task(self.connect_to_server(server_name))
            tasks.append(task)
        
        if tasks:
            logger.debug(f"Executing {len(tasks)} connection tasks concurrently...")
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(task_results):
                server_name = server_names[i]
                if isinstance(result, Exception):
                    logger.error(f"Failed to connect to server {server_name}: {result}")
                    results[server_name] = False
                elif result:
                    logger.info(f"Successfully connected to server: {server_name}")
                    results[server_name] = True
                else:
                    logger.warning(f"Warning: Failed to connect to server: {server_name}")
                    results[server_name] = False
        
        successful_connections = sum(1 for success in results.values() if success)
        total_servers = len(results)
        logger.info(f"Connection summary: {successful_connections}/{total_servers} servers connected successfully")
        
        return results
    
    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers"""
        tasks = []
        for server_name in self._connections:
            task = asyncio.create_task(self.disconnect_from_server(server_name))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
        logger.info("Disconnected from all MCP servers")
    
    
    def get_all_connections(self) -> Dict[str, ConnectionInfo]:
        """Get information about all connections"""
        return self._connections.copy()
    
    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names"""
        return [
            name for name, info in self._connections.items()
            if info.status == ConnectionStatus.CONNECTED
        ]
    
    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connections"""
        health_status = {}
        
        for server_name, connection_info in self._connections.items():
            if connection_info.status == ConnectionStatus.CONNECTED and connection_info.session:
                try:
                    # Try to list tools as a health check
                    await connection_info.session.list_tools()
                    health_status[server_name] = True
                except Exception as e:
                    logger.warning("Health check failed for server %s: %s", server_name, e)
                    health_status[server_name] = False
                    
                    # Update connection status
                    connection_info.status = ConnectionStatus.ERROR
                    connection_info.last_error = str(e)
            else:
                health_status[server_name] = False
        
        return health_status
    
    async def cleanup(self) -> None:
        """Cleanup resources and close all connections"""
        logger.info("Cleaning up MCP Connection Manager")
        
        # Disconnect from all servers
        await self.disconnect_all()
        
        # Reset state
        self._connections.clear()
        self._mcp_client = None
        self._initialized = False
        
        logger.info("MCP Connection Manager cleanup completed")


# Global instance
mcp_connection_manager = MCPConnectionManager()