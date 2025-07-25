"""
MCP Integration Layer for GenPod AI Backend

This module provides a complete MCP (Model Context Protocol) integration layer
that allows GenPod agents to access tools and resources from external MCP servers.

Components:
- ConfigManager: Handles MCP server configuration
- ConnectionManager: Manages connections to MCP servers
- ToolRegistry: Discovers and catalogs available tools
- ToolProcessor: Executes tools with validation and error handling
- MCPManager: High-level orchestrator and agent interface

Usage:
    from core.mcp import mcp_manager
    
    # Initialize the MCP system
    success, message = await mcp_manager.initialize()
    
    # Get MCP instance for agent use
    mcp_instance = mcp_manager.get_mcp_instance()
    
    # Execute tools
    result = await mcp_instance.execute_tool('tool_name', {'param': 'value'})
"""

from .config_manager import mcp_config_manager
from .connection_manager import mcp_connection_manager
from .tool_registry import mcp_tool_registry
from .tool_processor import mcp_tool_processor, MCPToolResult, ToolExecutionStatus
from .mcp_manager import mcp_manager, MCPSystemStatus, MCPSystemInfo

__all__ = [
    'mcp_config_manager',
    'mcp_connection_manager', 
    'mcp_tool_registry',
    'mcp_tool_processor',
    'mcp_manager',
    'MCPToolResult',
    'ToolExecutionStatus',
    'MCPSystemStatus',
    'MCPSystemInfo'
]

# Version info
__version__ = "1.0.0"
__author__ = "GenPod AI Team"
__description__ = "MCP Integration Layer for GenPod AI Backend"