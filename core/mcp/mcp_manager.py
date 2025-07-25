"""
MCP Manager for GenPod AI Backend Integration Layer

This module provides the high-level orchestration layer for MCP integration.
It coordinates all MCP components and provides a unified interface for
GenPod agents to access MCP tools and resources.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import time

from utils.logger import logger
from core.decorators.singleton import singleton
from core.mcp.config_manager import mcp_config_manager
from core.mcp.connection_manager import mcp_connection_manager
from core.mcp.tool_registry import mcp_tool_registry
from core.mcp.tool_processor import mcp_tool_processor, MCPToolResult, ToolExecutionStatus
from llms.llm import LLM


class MCPSystemStatus(Enum):
    """Status of the MCP system"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    ERROR = "error"


@dataclass
class MCPSystemInfo:
    """Information about the MCP system status"""
    status: MCPSystemStatus
    connected_servers: List[str]
    available_tools: int
    available_resources: int
    available_prompts: int
    last_discovery: Optional[float] = None
    initialization_time: Optional[float] = None
    errors: List[str] = None


@singleton
class MCPManager:
    """
    MCP Manager - High-level orchestrator for MCP Integration Layer
    
    This singleton class provides the main interface for GenPod agents
    to interact with MCP tools and resources. It coordinates all MCP
    components and handles system-wide operations.
    """
    
    def __init__(self):
        self._status = MCPSystemStatus.UNINITIALIZED
        self._initialization_time: Optional[float] = None
        self._last_system_check: Optional[float] = None
        self._system_errors: List[str] = []
        self._lock = asyncio.Lock()
    
    async def initialize(self, auto_connect: bool = True, auto_discover: bool = True) -> tuple[bool, str]:
        """Initialize the MCP system.
        
        Args:
            auto_connect: Whether to automatically connect to all enabled servers.
            auto_discover: Whether to automatically discover tools after connection.
            
        Returns:
            tuple[bool, str]: (success, message) following GenPod convention.
        """
        async with self._lock:
            if self._status != MCPSystemStatus.UNINITIALIZED:
                logger.info(f"MCP system already initialized with status: {self._status.value}")
                return True, "MCP system already initialized"
            
            self._status = MCPSystemStatus.INITIALIZING
            start_time = time.time()
            
            try:
                logger.info("Starting MCP system initialization...")
                logger.info(f"Configuration: auto_connect={auto_connect}, auto_discover={auto_discover}")
                
                # Clear any previous errors
                self._system_errors.clear()
                
                # Step 1: Initialize configuration manager
                try:
                    logger.info("Initializing configuration manager...")
                    await mcp_config_manager.initialize()
                    logger.info("Configuration manager initialized successfully")
                except Exception as e:
                    error_msg = f"Failed to initialize configuration manager: {e}"
                    logger.error(f"Failed to initialize: {error_msg}", exc_info=True)
                    self._system_errors.append(error_msg)
                    self._status = MCPSystemStatus.ERROR
                    return False, error_msg
                
                # Step 2: Initialize connection manager
                try:
                    logger.info("Initializing connection manager...")
                    await mcp_connection_manager.initialize()
                    logger.info("Connection manager initialized successfully")
                except Exception as e:
                    error_msg = f"Failed to initialize connection manager: {e}"
                    logger.error(f"Failed to initialize: {error_msg}", exc_info=True)
                    self._system_errors.append(error_msg)
                    self._status = MCPSystemStatus.ERROR
                    return False, error_msg
                
                # Step 3: Initialize tool registry
                try:
                    logger.info("Initializing tool registry...")
                    await mcp_tool_registry.initialize()
                    logger.info("Tool registry initialized successfully")
                except Exception as e:
                    error_msg = f"Failed to initialize tool registry: {e}"
                    logger.error(f"Failed to initialize: {error_msg}", exc_info=True)
                    self._system_errors.append(error_msg)
                    self._status = MCPSystemStatus.ERROR
                    return False, error_msg
                
                # Step 4: Initialize tool processor
                try:
                    logger.info("Initializing tool processor...")
                    await mcp_tool_processor.initialize()
                    logger.info("Tool processor initialized successfully")
                except Exception as e:
                    error_msg = f"Failed to initialize tool processor: {e}"
                    logger.error(f"Failed to initialize: {error_msg}", exc_info=True)
                    self._system_errors.append(error_msg)
                    self._status = MCPSystemStatus.ERROR
                    return False, error_msg
                
                # Step 5: Auto-connect if requested
                if auto_connect:
                    try:
                        logger.info("Connecting to enabled MCP servers...")
                        connect_results = await mcp_connection_manager.connect_to_all_enabled_servers()
                        connected_count = sum(1 for success in connect_results.values() if success)
                        total_servers = len(connect_results)
                        
                        if connected_count == 0:
                            logger.warning("Warning: No servers connected successfully")
                            self._status = MCPSystemStatus.DEGRADED
                        else:
                            logger.info(f"Successfully connected to {connected_count}/{total_servers} servers")
                            for server_name, success in connect_results.items():
                                if success:
                                    logger.info(f"  Successfully connected to {server_name}")
                                else:
                                    logger.warning(f"  Failed to connect to {server_name}")
                            
                    except Exception as e:
                        error_msg = f"Failed to connect to servers: {e}"
                        logger.error(f"Failed to connect: {error_msg}", exc_info=True)
                        self._system_errors.append(error_msg)
                        self._status = MCPSystemStatus.DEGRADED
                
                # Step 6: Auto-discover tools if requested
                if auto_discover:
                    try:
                        logger.info("Discovering tools from connected servers...")
                        discovery_results = await mcp_tool_registry.discover_all_tools()
                        discovered_count = sum(1 for success in discovery_results.values() if success)
                        total_servers = len(discovery_results)
                        
                        if discovered_count == 0:
                            logger.warning("Warning: No tools discovered from any server")
                            self._status = MCPSystemStatus.DEGRADED
                        else:
                            logger.info(f"Successfully discovered tools from {discovered_count}/{total_servers} servers")
                            
                            # Log tool discovery details
                            summary = mcp_tool_registry.get_discovery_summary()
                            logger.info(f"Discovery summary: {summary['total_tools']} tools, {summary['total_resources']} resources, {summary['total_prompts']} prompts")
                            
                    except Exception as e:
                        error_msg = f"Failed to discover tools: {e}"
                        logger.error(f"Failed to discover tools: {error_msg}", exc_info=True)
                        self._system_errors.append(error_msg)
                        self._status = MCPSystemStatus.DEGRADED
                
                # Set final status
                if self._status == MCPSystemStatus.INITIALIZING:
                    self._status = MCPSystemStatus.READY
                
                self._initialization_time = time.time() - start_time
                logger.info(f"MCP system initialized successfully in {self._initialization_time:.2f}s with status: {self._status.value}")
                
                return True, f"MCP system initialized successfully in {self._initialization_time:.2f}s"
                
            except Exception as e:
                error_msg = f"Unexpected error during MCP system initialization: {e}"
                logger.error(f"Unexpected error: {error_msg}", exc_info=True)
                self._system_errors.append(error_msg)
                self._status = MCPSystemStatus.ERROR
                return False, error_msg
    
    async def get_system_info(self) -> MCPSystemInfo:
        """Get comprehensive system information"""
        try:
            # Get connected servers
            connected_servers = mcp_connection_manager.get_connected_servers()
            
            # Get discovery summary
            discovery_summary = mcp_tool_registry.get_discovery_summary()
            
            return MCPSystemInfo(
                status=self._status,
                connected_servers=connected_servers,
                available_tools=discovery_summary.get("available_tools", 0),
                available_resources=discovery_summary.get("total_resources", 0),
                available_prompts=discovery_summary.get("total_prompts", 0),
                last_discovery=discovery_summary.get("last_discovery"),
                initialization_time=self._initialization_time,
                errors=self._system_errors.copy()
            )
            
        except Exception as e:
            logger.error("Failed to get system info: %s", e)
            return MCPSystemInfo(
                status=MCPSystemStatus.ERROR,
                connected_servers=[],
                available_tools=0,
                available_resources=0,
                available_prompts=0,
                errors=[str(e)]
            )
    
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any],
        server_name: Optional[str] = None
    ) -> MCPToolResult:
        """
        Execute an MCP tool through the unified interface
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            server_name: Optional server name to scope the tool lookup
            
        Returns:
            MCPToolResult with execution results
        """
        if self._status not in [MCPSystemStatus.READY, MCPSystemStatus.DEGRADED]:
            return MCPToolResult(
                tool_name=tool_name,
                server_name=server_name or "unknown",
                status=ToolExecutionStatus.SERVER_ERROR,
                error=f"MCP system not ready (status: {self._status.value})",
                parameters=parameters
            )
        
        try:
            return await mcp_tool_processor.execute_tool(tool_name, parameters, server_name)
        except Exception as e:
            logger.error("Failed to execute tool %s: %s", tool_name, e)
            return MCPToolResult(
                tool_name=tool_name,
                server_name=server_name or "unknown",
                status=ToolExecutionStatus.SERVER_ERROR,
                error=f"Execution failed: {e}",
                parameters=parameters
            )
    
    async def execute_tools_batch(
        self, 
        tool_requests: List[Dict[str, Any]]
    ) -> List[MCPToolResult]:
        """
        Execute multiple MCP tools in batch
        
        Args:
            tool_requests: List of tool requests with 'tool_name', 'parameters', and optional 'server_name'
            
        Returns:
            List of MCPToolResult objects
        """
        if self._status not in [MCPSystemStatus.READY, MCPSystemStatus.DEGRADED]:
            error_results = []
            for request in tool_requests:
                error_results.append(MCPToolResult(
                    tool_name=request.get('tool_name', 'unknown'),
                    server_name=request.get('server_name', 'unknown'),
                    status=ToolExecutionStatus.SERVER_ERROR,
                    error=f"MCP system not ready (status: {self._status.value})",
                    parameters=request.get('parameters', {})
                ))
            return error_results
        
        try:
            return await mcp_tool_processor.execute_tools_batch(tool_requests)
        except Exception as e:
            logger.error("Failed to execute tools batch: %s", e)
            # Return error results for all requests
            error_results = []
            for request in tool_requests:
                error_results.append(MCPToolResult(
                    tool_name=request.get('tool_name', 'unknown'),
                    server_name=request.get('server_name', 'unknown'),
                    status=ToolExecutionStatus.SERVER_ERROR,
                    error=f"Batch execution failed: {e}",
                    parameters=request.get('parameters', {})
                ))
            return error_results
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        if self._status not in [MCPSystemStatus.READY, MCPSystemStatus.DEGRADED]:
            return []
        
        try:
            return mcp_tool_processor.get_available_tools()
        except Exception as e:
            logger.error("Failed to get available tools: %s", e)
            return []
    
    def get_tool_info(self, tool_name: str, server_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get detailed information about a tool"""
        if self._status not in [MCPSystemStatus.READY, MCPSystemStatus.DEGRADED]:
            return None
        
        try:
            return mcp_tool_processor.get_tool_info(tool_name, server_name)
        except Exception as e:
            logger.error("Failed to get tool info for %s: %s", tool_name, e)
            return None
    
    def get_tools_by_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Get all tools available on a specific server"""
        if self._status not in [MCPSystemStatus.READY, MCPSystemStatus.DEGRADED]:
            return []
        
        try:
            return mcp_tool_processor.get_tools_by_server(server_name)
        except Exception as e:
            logger.error("Failed to get tools for server %s: %s", server_name, e)
            return []
    
    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """Search for tools by name or description"""
        if self._status not in [MCPSystemStatus.READY, MCPSystemStatus.DEGRADED]:
            return []
        
        try:
            return mcp_tool_processor.search_tools(query)
        except Exception as e:
            logger.error("Failed to search tools with query '%s': %s", query, e)
            return []
    
    async def refresh_connections(self) -> tuple[bool, str]:
        """
        Refresh all MCP server connections
        
        Returns:
            tuple[bool, str]: (success, message) following GenPod convention
        """
        try:
            logger.info("Refreshing MCP connections...")
            
            # Disconnect all current connections
            await mcp_connection_manager.disconnect_all()
            
            # Reconnect to all enabled servers
            connect_results = await mcp_connection_manager.connect_to_all_enabled_servers()
            
            connected_count = sum(1 for success in connect_results.values() if success)
            total_servers = len(connect_results)
            
            if connected_count == 0:
                self._status = MCPSystemStatus.DEGRADED
                return False, "No servers connected after refresh"
            
            # Update status if we have connections
            if self._status == MCPSystemStatus.DEGRADED and connected_count > 0:
                self._status = MCPSystemStatus.READY
            
            logger.info(f"Connection refresh completed: {connected_count}/{total_servers} servers connected")
            return True, f"Connected to {connected_count}/{total_servers} servers"
            
        except Exception as e:
            error_msg = f"Failed to refresh connections: {e}"
            logger.error(error_msg, exc_info=True)
            self._status = MCPSystemStatus.ERROR
            return False, error_msg
    
    async def refresh_tools(self) -> tuple[bool, str]:
        """
        Refresh tool discovery from all servers
        
        Returns:
            tuple[bool, str]: (success, message) following GenPod convention
        """
        try:
            logger.info("Refreshing MCP tool discovery...")
            
            # Refresh tool discovery
            discovery_results = await mcp_tool_registry.refresh_tool_discovery()
            
            discovered_count = sum(1 for success in discovery_results.values() if success)
            total_servers = len(discovery_results)
            
            if discovered_count == 0:
                return False, "No tools discovered from any server"
            
            # Get summary of discovered tools
            summary = mcp_tool_registry.get_discovery_summary()
            tools_count = summary.get("available_tools", 0)
            
            logger.info(f"Tool discovery refresh completed: {tools_count} tools from {discovered_count}/{total_servers} servers")
            return True, f"Discovered {tools_count} tools from {discovered_count}/{total_servers} servers"
            
        except Exception as e:
            error_msg = f"Failed to refresh tools: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    async def health_check(self) -> tuple[bool, str]:
        """
        Perform a comprehensive health check of the MCP system
        
        Returns:
            tuple[bool, str]: (healthy, status_message) following GenPod convention
        """
        try:
            health_issues = []
            
            # Check system status
            if self._status == MCPSystemStatus.ERROR:
                health_issues.append("System is in error state")
            elif self._status == MCPSystemStatus.UNINITIALIZED:
                health_issues.append("System is not initialized")
            
            # Check server connections
            connected_servers = mcp_connection_manager.get_connected_servers()
            if not connected_servers:
                health_issues.append("No servers connected")
            
            # Check tool availability
            available_tools = self.get_available_tools()
            if not available_tools:
                health_issues.append("No tools available")
            
            # Check for recent errors
            if self._system_errors:
                health_issues.append(f"Recent system errors: {len(self._system_errors)}")
            
            # Update last system check
            self._last_system_check = time.time()
            
            if health_issues:
                health_message = f"Health issues detected: {', '.join(health_issues)}"
                logger.warning(health_message)
                return False, health_message
            else:
                health_message = f"System healthy: {len(connected_servers)} servers, {len(available_tools)} tools"
                logger.info(health_message)
                return True, health_message
                
        except Exception as e:
            error_msg = f"Health check failed: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    async def shutdown(self) -> tuple[bool, str]:
        """
        Gracefully shutdown the MCP system
        
        Returns:
            tuple[bool, str]: (success, message) following GenPod convention
        """
        try:
            logger.info("Shutting down MCP system...")
            
            # Cleanup components in reverse order
            await mcp_tool_processor.cleanup()
            await mcp_tool_registry.cleanup()
            await mcp_connection_manager.cleanup()
            
            # Reset state
            self._status = MCPSystemStatus.UNINITIALIZED
            self._initialization_time = None
            self._last_system_check = None
            self._system_errors.clear()
            
            logger.info("MCP system shutdown completed")
            return True, "MCP system shutdown completed"
            
        except Exception as e:
            error_msg = f"Failed to shutdown MCP system: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    # Agent Integration Methods
    
    def get_mcp_instance(self) -> 'MCPManager':
        """
        Get the MCP Manager instance for agent integration
        
        This method provides a way for GenPod agents to get access to the
        MCP system instance, following the user's feedback about passing
        the MCP instance to agents rather than using agent_access patterns.
        
        Returns:
            MCPManager: The singleton MCP Manager instance
        """
        return self
    
    def is_ready(self) -> bool:
        """Check if the MCP system is ready for use"""
        return self._status in [MCPSystemStatus.READY, MCPSystemStatus.DEGRADED]
    
    def get_status(self) -> MCPSystemStatus:
        """Get the current system status"""
        return self._status
    
    async def execute_task(self, task: str, context: Dict[str, Any], llm: LLM) -> 'TaskResult':
        """
        Execute task using LLM-driven tool selection and parameter mapping
        
        Args:
            task: Description of the task to execute
            context: Context data available for parameter mapping
            llm: LLM instance to use for tool selection and parameter mapping
            
        Returns:
            TaskResult containing execution results
        """
        # Import here to avoid circular imports
        from core.mcp.mcp_task_handler import mcp_task_handler
        
        if self._status not in [MCPSystemStatus.READY, MCPSystemStatus.DEGRADED]:
            # Import TaskResult here to avoid circular imports
            from core.mcp.mcp_task_handler import TaskResult
            return TaskResult(
                success=False,
                result=None,
                tool_used="unknown",
                execution_time=0.0,
                error=f"MCP system not ready (status: {self._status.value})"
            )
        
        return await mcp_task_handler.execute_task(task, context, llm)


# Global instance
mcp_manager = MCPManager()
