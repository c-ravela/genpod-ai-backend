"""
Tool Registry for MCP Integration Layer

This module discovers and catalogs available tools from connected MCP servers.
It provides a unified registry of all available MCP tools across servers,
handling tool metadata, schemas, and discovery.
"""

import asyncio
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import time
import json

from utils.logger import logger
from core.decorators.singleton import singleton
from core.mcp.connection_manager import mcp_connection_manager
from core.mcp.config_manager import mcp_config_manager


class ToolStatus(Enum):
    """Status of a tool in the registry"""
    DISCOVERED = "discovered"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass
class MCPToolInfo:
    """Information about a discovered MCP tool"""
    name: str
    server_name: str
    description: str
    status: ToolStatus
    schema: Optional[Dict[str, Any]] = None
    input_schema: Optional[Dict[str, Any]] = None
    last_discovered: Optional[float] = None
    last_error: Optional[str] = None
    capabilities: Set[str] = field(default_factory=set)


@dataclass
class MCPResourceInfo:
    """Information about a discovered MCP resource"""
    uri: str
    server_name: str
    name: str
    description: str
    mime_type: Optional[str] = None
    last_discovered: Optional[float] = None


@dataclass
class MCPPromptInfo:
    """Information about a discovered MCP prompt"""
    name: str
    server_name: str
    description: str
    arguments: Optional[List[Dict[str, Any]]] = None
    last_discovered: Optional[float] = None


@dataclass
class ServerDiscoveryInfo:
    """Information about tool discovery from a server"""
    server_name: str
    tools_count: int
    resources_count: int
    prompts_count: int
    last_discovery: Optional[float] = None
    last_error: Optional[str] = None
    discovery_duration: Optional[float] = None


@singleton
class MCPToolRegistry:
    """
    Tool Registry for MCP Integration Layer
    
    Singleton class that discovers and catalogs available tools, resources,
    and prompts from connected MCP servers.
    """
    
    def __init__(self):
        self._tools: Dict[str, MCPToolInfo] = {}  # tool_name -> MCPToolInfo
        self._tool_name_index: Dict[str, List[str]] = {}  # tool_name -> List[tool_keys] for fast lookup
        self._resources: Dict[str, MCPResourceInfo] = {}  # resource_uri -> MCPResourceInfo
        self._prompts: Dict[str, MCPPromptInfo] = {}  # prompt_name -> MCPPromptInfo
        self._prompt_name_index: Dict[str, List[str]] = {}  # prompt_name -> List[prompt_keys] for fast lookup
        self._server_discovery: Dict[str, ServerDiscoveryInfo] = {}  # server_name -> ServerDiscoveryInfo
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the tool registry"""
        if self._initialized:
            return
        
        try:
            # Ensure connection manager is initialized
            await mcp_connection_manager.initialize()
            
            self._initialized = True
            logger.info("MCP Tool Registry initialized")
            
        except Exception as e:
            logger.error("Failed to initialize MCP Tool Registry: %s", e, exc_info=True)
            raise
    
    async def discover_tools_from_server(self, server_name: str) -> bool:
        """
        Discover tools, resources, and prompts from a specific MCP server
        
        Args:
            server_name: Name of the server to discover from
            
        Returns:
            True if discovery successful, False otherwise
        """
        if not self._initialized:
            logger.debug("Tool registry not initialized, initializing now...")
            await self.initialize()
        
        start_time = time.time()
        
        try:
            logger.info(f"Discovering tools from MCP server: {server_name}")
            
            # Get connection session
            session = await mcp_connection_manager.get_connection(server_name)
            if not session:
                logger.warning(f"Warning: No connection available for server: {server_name}")
                return False
            
            tools_count = 0
            resources_count = 0
            prompts_count = 0
            
            async with self._lock:
                # Discover tools
                try:
                    logger.debug(f"Listing tools from server: {server_name}")
                    tools = await session.connector.list_tools()
                    tools_count = len(tools) if tools else 0
                    logger.debug(f"Found {tools_count} tools on server {server_name}")
                    
                    if tools:
                        for tool in tools:
                            tool_info = MCPToolInfo(
                                name=tool.name,
                                server_name=server_name,
                                description=tool.description or "",
                                status=ToolStatus.AVAILABLE,
                                schema=getattr(tool, 'inputSchema', None),
                                input_schema=getattr(tool, 'inputSchema', None),
                                last_discovered=time.time(),
                                capabilities=set()
                            )
                            
                            # Create unique tool key (server_name:tool_name)
                            tool_key = f"{server_name}:{tool.name}"
                            self._tools[tool_key] = tool_info
                            
                            # Update name index for fast lookup
                            if tool.name not in self._tool_name_index:
                                self._tool_name_index[tool.name] = []
                            self._tool_name_index[tool.name].append(tool_key)
                            
                            logger.debug(f"  Tool discovered: {tool.name} (description: {tool.description})")
                    
                except Exception as e:
                    logger.warning(f"Warning: Failed to discover tools from server {server_name}: {e}")
                
                # Discover resources
                try:
                    logger.debug(f"Listing resources from server: {server_name}")
                    resources = await session.connector.list_resources()
                    resources_count = len(resources) if resources else 0
                    logger.debug(f"Found {resources_count} resources on server {server_name}")
                    
                    if resources:
                        for resource in resources:
                            resource_info = MCPResourceInfo(
                                uri=resource.uri,
                                server_name=server_name,
                                name=resource.name or resource.uri,
                                description=resource.description or "",
                                mime_type=getattr(resource, 'mimeType', None),
                                last_discovered=time.time()
                            )
                            
                            self._resources[resource.uri] = resource_info
                            
                            logger.debug(f"  Resource discovered: {resource.uri}")
                    
                except Exception as e:
                    logger.warning(f"Warning: Failed to discover resources from server {server_name}: {e}")
                
                # Discover prompts
                try:
                    logger.debug(f"Listing prompts from server: {server_name}")
                    prompts = await session.connector.list_prompts()
                    prompts_count = len(prompts) if prompts else 0
                    logger.debug(f"Found {prompts_count} prompts on server {server_name}")
                    
                    if prompts:
                        for prompt in prompts:
                            prompt_info = MCPPromptInfo(
                                name=prompt.name,
                                server_name=server_name,
                                description=prompt.description or "",
                                arguments=getattr(prompt, 'arguments', None),
                                last_discovered=time.time()
                            )
                            
                            # Create unique prompt key (server_name:prompt_name)
                            prompt_key = f"{server_name}:{prompt.name}"
                            self._prompts[prompt_key] = prompt_info
                            
                            # Update name index for fast lookup
                            if prompt.name not in self._prompt_name_index:
                                self._prompt_name_index[prompt.name] = []
                            self._prompt_name_index[prompt.name].append(prompt_key)
                            
                            logger.debug(f"  Prompt discovered: {prompt.name}")
                    
                except Exception as e:
                    logger.warning(f"Warning: Failed to discover prompts from server {server_name}: {e}")
                
                # Update server discovery info
                discovery_duration = time.time() - start_time
                self._server_discovery[server_name] = ServerDiscoveryInfo(
                    server_name=server_name,
                    tools_count=tools_count,
                    resources_count=resources_count,
                    prompts_count=prompts_count,
                    last_discovery=time.time(),
                    last_error=None,
                    discovery_duration=discovery_duration
                )
            
            logger.info(f"Successfully discovered from server {server_name}: {tools_count} tools, {resources_count} resources, {prompts_count} prompts in {discovery_duration:.2f}s")
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to discover tools from server {server_name}: {e}"
            logger.error(f"Failed to discover tools: {error_msg}", exc_info=True)
            
            # Update server discovery info with error
            self._server_discovery[server_name] = ServerDiscoveryInfo(
                server_name=server_name,
                tools_count=0,
                resources_count=0,
                prompts_count=0,
                last_discovery=time.time(),
                last_error=str(e),
                discovery_duration=time.time() - start_time
            )
            
            return False
    
    async def discover_all_tools(self) -> Dict[str, bool]:
        """
        Discover tools from all connected MCP servers
        
        Returns:
            Dictionary mapping server names to discovery success status
        """
        if not self._initialized:
            await self.initialize()
        
        logger.info("Discovering tools from all connected MCP servers")
        
        # Get all connected servers
        connected_servers = mcp_connection_manager.get_connected_servers()
        
        if not connected_servers:
            logger.warning("No connected MCP servers found for tool discovery")
            return {}
        
        # Discover tools from all servers concurrently
        tasks = []
        for server_name in connected_servers:
            task = asyncio.create_task(self.discover_tools_from_server(server_name))
            tasks.append((server_name, task))
        
        results = {}
        if tasks:
            # Wait for all discovery tasks to complete
            for server_name, task in tasks:
                try:
                    result = await task
                    results[server_name] = result
                except Exception as e:
                    logger.error("Discovery task failed for server %s: %s", server_name, e)
                    results[server_name] = False
        
        successful_discoveries = sum(1 for success in results.values() if success)
        logger.info("Tool discovery completed: %d/%d servers successful", 
                   successful_discoveries, len(results))
        
        return results
    
    def get_tool(self, tool_name: str, server_name: Optional[str] = None) -> Optional[MCPToolInfo]:
        """
        Get tool information by name
        
        Args:
            tool_name: Name of the tool
            server_name: Optional server name to scope the search
            
        Returns:
            MCPToolInfo if found, None otherwise
        """
        if server_name:
            # Look for specific server tool
            tool_key = f"{server_name}:{tool_name}"
            return self._tools.get(tool_key)
        else:
            # Use index for fast lookup across all servers
            tool_keys = self._tool_name_index.get(tool_name, [])
            if tool_keys:
                # Return the first available tool (could be improved with priority logic)
                return self._tools.get(tool_keys[0])
            return None
    
    def get_all_tools(self) -> Dict[str, MCPToolInfo]:
        """Get all discovered tools"""
        return self._tools.copy()
    
    def get_tools_by_server(self, server_name: str) -> List[MCPToolInfo]:
        """Get all tools from a specific server"""
        return [
            tool_info for tool_info in self._tools.values()
            if tool_info.server_name == server_name
        ]
    
    def get_available_tools(self) -> List[MCPToolInfo]:
        """Get all available tools"""
        return [
            tool_info for tool_info in self._tools.values()
            if tool_info.status == ToolStatus.AVAILABLE
        ]
    
    def get_tool_names(self) -> List[str]:
        """Get list of all tool names"""
        return [tool_info.name for tool_info in self._tools.values()]
    
    def get_tool_names_by_server(self, server_name: str) -> List[str]:
        """Get tool names from a specific server"""
        return [
            tool_info.name for tool_info in self._tools.values()
            if tool_info.server_name == server_name
        ]
    
    def get_resource(self, resource_uri: str) -> Optional[MCPResourceInfo]:
        """Get resource information by URI"""
        return self._resources.get(resource_uri)
    
    def get_all_resources(self) -> Dict[str, MCPResourceInfo]:
        """Get all discovered resources"""
        return self._resources.copy()
    
    def get_resources_by_server(self, server_name: str) -> List[MCPResourceInfo]:
        """Get all resources from a specific server"""
        return [
            resource_info for resource_info in self._resources.values()
            if resource_info.server_name == server_name
        ]
    
    def get_prompt(self, prompt_name: str, server_name: Optional[str] = None) -> Optional[MCPPromptInfo]:
        """
        Get prompt information by name
        
        Args:
            prompt_name: Name of the prompt
            server_name: Optional server name to scope the search
            
        Returns:
            MCPPromptInfo if found, None otherwise
        """
        if server_name:
            # Look for specific server prompt
            prompt_key = f"{server_name}:{prompt_name}"
            return self._prompts.get(prompt_key)
        else:
            # Use index for fast lookup across all servers
            prompt_keys = self._prompt_name_index.get(prompt_name, [])
            if prompt_keys:
                # Return the first available prompt (could be improved with priority logic)
                return self._prompts.get(prompt_keys[0])
            return None
    
    def get_all_prompts(self) -> Dict[str, MCPPromptInfo]:
        """Get all discovered prompts"""
        return self._prompts.copy()
    
    def get_prompts_by_server(self, server_name: str) -> List[MCPPromptInfo]:
        """Get all prompts from a specific server"""
        return [
            prompt_info for prompt_info in self._prompts.values()
            if prompt_info.server_name == server_name
        ]
    
    def get_server_discovery_info(self, server_name: str) -> Optional[ServerDiscoveryInfo]:
        """Get discovery information for a specific server"""
        return self._server_discovery.get(server_name)
    
    def get_all_server_discovery_info(self) -> Dict[str, ServerDiscoveryInfo]:
        """Get discovery information for all servers"""
        return self._server_discovery.copy()
    
    def get_discovery_summary(self) -> Dict[str, Any]:
        """Get a summary of all discoveries"""
        total_tools = len(self._tools)
        total_resources = len(self._resources)
        total_prompts = len(self._prompts)
        
        servers_with_tools = len(set(tool.server_name for tool in self._tools.values()))
        servers_with_resources = len(set(resource.server_name for resource in self._resources.values()))
        servers_with_prompts = len(set(prompt.server_name for prompt in self._prompts.values()))
        
        available_tools = len(self.get_available_tools())
        
        return {
            "total_tools": total_tools,
            "total_resources": total_resources,
            "total_prompts": total_prompts,
            "available_tools": available_tools,
            "servers_with_tools": servers_with_tools,
            "servers_with_resources": servers_with_resources,
            "servers_with_prompts": servers_with_prompts,
            "discovery_servers": list(self._server_discovery.keys()),
            "last_discovery": max(
                (info.last_discovery for info in self._server_discovery.values() if info.last_discovery),
                default=None
            )
        }
    
    def search_tools(self, query: str) -> List[MCPToolInfo]:
        """
        Search tools by name or description
        
        Args:
            query: Search query (case-insensitive)
            
        Returns:
            List of matching tools
        """
        query_lower = query.lower()
        matching_tools = []
        
        for tool_info in self._tools.values():
            if (query_lower in tool_info.name.lower() or 
                query_lower in tool_info.description.lower()):
                matching_tools.append(tool_info)
        
        return matching_tools
    
    async def refresh_tool_discovery(self) -> Dict[str, bool]:
        """
        Refresh tool discovery for all servers
        
        Returns:
            Dictionary mapping server names to refresh success status
        """
        logger.info("Refreshing tool discovery for all servers")
        
        # Clear existing discoveries
        async with self._lock:
            self._tools.clear()
            self._tool_name_index.clear()
            self._resources.clear()
            self._prompts.clear()
            self._prompt_name_index.clear()
            self._server_discovery.clear()
        
        # Rediscover all tools
        return await self.discover_all_tools()
    
    def is_tool_available(self, tool_name: str, server_name: Optional[str] = None) -> bool:
        """Check if a tool is available"""
        tool_info = self.get_tool(tool_name, server_name)
        return tool_info is not None and tool_info.status == ToolStatus.AVAILABLE
    
    def get_tool_schema(self, tool_name: str, server_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the schema for a specific tool"""
        tool_info = self.get_tool(tool_name, server_name)
        return tool_info.schema if tool_info else None
    
    async def cleanup(self) -> None:
        """Cleanup registry and clear all data"""
        logger.info("Cleaning up MCP Tool Registry")
        
        async with self._lock:
            self._tools.clear()
            self._tool_name_index.clear()
            self._resources.clear()
            self._prompts.clear()
            self._prompt_name_index.clear()
            self._server_discovery.clear()
        
        self._initialized = False
        logger.info("MCP Tool Registry cleanup completed")


# Global instance
mcp_tool_registry = MCPToolRegistry()