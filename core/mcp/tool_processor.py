"""
Tool Processor for MCP Integration Layer

This module handles the execution of MCP tools with proper parameter validation,
error handling, and result processing. It provides a unified interface for
agents to execute MCP tools from any connected server.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import time
from collections import defaultdict, deque

from jsonschema import validate, ValidationError
from utils.logger import logger
from core.decorators.singleton import singleton
from core.mcp.connection_manager import mcp_connection_manager
from core.mcp.tool_registry import mcp_tool_registry
from core.mcp.config_manager import mcp_config_manager


class ToolExecutionStatus(Enum):
    """Status of tool execution"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NOT_FOUND = "not_found"
    INVALID_PARAMS = "invalid_params"
    SERVER_ERROR = "server_error"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


class CircuitBreakerState(Enum):
    """States of circuit breaker"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for tool execution"""
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    last_failure_time: Optional[float] = None
    failures: deque = None
    
    def __post_init__(self):
        if self.failures is None:
            self.failures = deque(maxlen=10)  # Keep last 10 failures


@dataclass
class MCPToolResult:
    """Result of MCP tool execution"""
    tool_name: str
    server_name: str
    status: ToolExecutionStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    parameters: Optional[Dict[str, Any]] = None


@singleton
class MCPToolProcessor:
    """
    Tool Processor for MCP Integration Layer
    
    Singleton class that handles execution of MCP tools with proper
    parameter validation, error handling, and result processing.
    """
    
    def __init__(self):
        self._initialized = False
        self._execution_cache: Dict[str, MCPToolResult] = {}
        self._schema_cache: Dict[str, Dict[str, Any]] = {}  # Cache for processed schemas
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}  # Per-tool circuit breakers
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize the tool processor"""
        if self._initialized:
            return
        
        try:
            # Ensure dependencies are initialized
            await mcp_connection_manager.initialize()
            await mcp_tool_registry.initialize()
            
            self._initialized = True
            logger.info("MCP Tool Processor initialized")
            
        except Exception as e:
            logger.error("Failed to initialize MCP Tool Processor: %s", e, exc_info=True)
            raise
    
    def _get_circuit_breaker(self, tool_key: str) -> CircuitBreaker:
        """Get or create circuit breaker for a tool"""
        if tool_key not in self._circuit_breakers:
            self._circuit_breakers[tool_key] = CircuitBreaker()
        return self._circuit_breakers[tool_key]
    
    def _check_circuit_breaker(self, tool_key: str) -> bool:
        """Check if circuit breaker allows execution"""
        circuit_breaker = self._get_circuit_breaker(tool_key)
        current_time = time.time()
        
        if circuit_breaker.state == CircuitBreakerState.CLOSED:
            return True
        elif circuit_breaker.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (circuit_breaker.last_failure_time and 
                current_time - circuit_breaker.last_failure_time > circuit_breaker.recovery_timeout):
                circuit_breaker.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        elif circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def _record_success(self, tool_key: str) -> None:
        """Record successful execution"""
        circuit_breaker = self._get_circuit_breaker(tool_key)
        circuit_breaker.failure_count = 0
        circuit_breaker.state = CircuitBreakerState.CLOSED
        circuit_breaker.last_failure_time = None
    
    def _record_failure(self, tool_key: str) -> None:
        """Record failed execution"""
        circuit_breaker = self._get_circuit_breaker(tool_key)
        circuit_breaker.failure_count += 1
        circuit_breaker.failures.append(time.time())
        circuit_breaker.last_failure_time = time.time()
        
        if circuit_breaker.failure_count >= circuit_breaker.failure_threshold:
            circuit_breaker.state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker opened for tool: %s", tool_key)
    
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any],
        server_name: Optional[str] = None
    ) -> MCPToolResult:
        """
        Execute an MCP tool with the given parameters
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            server_name: Optional server name to scope the tool lookup
            
        Returns:
            MCPToolResult with execution results
        """
        if not self._initialized:
            logger.debug("Tool processor not initialized, initializing now...")
            await self.initialize()
        
        start_time = time.time()
        
        try:
            logger.info(f"Executing MCP tool: {tool_name}")
            logger.debug(f"Tool parameters: {parameters}")
            if server_name:
                logger.debug(f"Target server: {server_name}")
            
            # Look up tool in registry
            tool_info = mcp_tool_registry.get_tool(tool_name, server_name)
            if not tool_info:
                error_msg = f"Tool '{tool_name}' not found"
                if server_name:
                    error_msg += f" on server '{server_name}'"
                
                logger.warning(f"Tool not found: {error_msg}")
                return MCPToolResult(
                    tool_name=tool_name,
                    server_name=server_name or "unknown",
                    status=ToolExecutionStatus.NOT_FOUND,
                    error=error_msg,
                    execution_time=time.time() - start_time,
                    parameters=parameters
                )
            
            logger.debug(f"Tool found on server: {tool_info.server_name}")
            
            # Check circuit breaker
            tool_key = f"{tool_info.server_name}:{tool_name}"
            if not self._check_circuit_breaker(tool_key):
                error_msg = f"Circuit breaker is open for tool '{tool_name}'"
                logger.warning(f"Circuit breaker open: {error_msg}")
                return MCPToolResult(
                    tool_name=tool_name,
                    server_name=tool_info.server_name,
                    status=ToolExecutionStatus.CIRCUIT_BREAKER_OPEN,
                    error=error_msg,
                    execution_time=time.time() - start_time,
                    parameters=parameters
                )
            
            # Check if tool is available
            if not mcp_tool_registry.is_tool_available(tool_name, tool_info.server_name):
                error_msg = f"Tool '{tool_name}' is not available on server '{tool_info.server_name}'"
                logger.warning(f"Tool unavailable: {error_msg}")
                return MCPToolResult(
                    tool_name=tool_name,
                    server_name=tool_info.server_name,
                    status=ToolExecutionStatus.NOT_FOUND,
                    error=error_msg,
                    execution_time=time.time() - start_time,
                    parameters=parameters
                )
            
            # Get connection session
            logger.debug(f"Getting connection for server: {tool_info.server_name}")
            session = await mcp_connection_manager.get_connection(tool_info.server_name)
            if not session:
                error_msg = f"No connection available for server '{tool_info.server_name}'"
                logger.error(f"Connection unavailable: {error_msg}")
                return MCPToolResult(
                    tool_name=tool_name,
                    server_name=tool_info.server_name,
                    status=ToolExecutionStatus.SERVER_ERROR,
                    error=error_msg,
                    execution_time=time.time() - start_time,
                    parameters=parameters
                )
            
            # Validate parameters if schema is available
            if tool_info.schema:
                logger.debug(f"Validating parameters against schema for tool: {tool_name}")
                # Get processed schema from cache or process it
                tool_key = f"{tool_info.server_name}:{tool_name}"
                if tool_key not in self._schema_cache:
                    processed_schema = tool_info.schema
                    if 'type' not in processed_schema:
                        processed_schema = {
                            'type': 'object',
                            'properties': processed_schema.get('properties', {}),
                            'required': processed_schema.get('required', [])
                        }
                    self._schema_cache[tool_key] = processed_schema
                    logger.debug(f"Schema cached for tool: {tool_key}")
                
                validation_result = self._validate_parameters(parameters, self._schema_cache[tool_key])
                if not validation_result.is_valid:
                    error_msg = f"Invalid parameters for tool '{tool_name}': {validation_result.error}"
                    logger.warning(f"Parameter validation failed: {error_msg}")
                    return MCPToolResult(
                        tool_name=tool_name,
                        server_name=tool_info.server_name,
                        status=ToolExecutionStatus.INVALID_PARAMS,
                        error=error_msg,
                        execution_time=time.time() - start_time,
                        parameters=parameters
                    )
                logger.debug("Parameter validation passed")
            else:
                logger.debug("No schema available for parameter validation")
            
            # Execute the tool
            try:
                logger.debug(f"Calling tool '{tool_name}' on server '{tool_info.server_name}'...")
                result = await session.connector.call_tool(tool_name, parameters)
                
                # Process result
                processed_result = self._process_tool_result(result)
                
                execution_time = time.time() - start_time
                logger.info(f"Tool '{tool_name}' executed successfully in {execution_time:.2f}s")
                
                # Record success in circuit breaker
                self._record_success(tool_key)
                
                return MCPToolResult(
                    tool_name=tool_name,
                    server_name=tool_info.server_name,
                    status=ToolExecutionStatus.SUCCESS,
                    result=processed_result,
                    execution_time=execution_time,
                    parameters=parameters
                )
                
            except asyncio.TimeoutError:
                error_msg = f"Tool '{tool_name}' execution timed out"
                logger.error(f"Execution timeout: {error_msg}")
                
                # Record failure in circuit breaker
                self._record_failure(tool_key)
                
                return MCPToolResult(
                    tool_name=tool_name,
                    server_name=tool_info.server_name,
                    status=ToolExecutionStatus.TIMEOUT,
                    error=error_msg,
                    execution_time=time.time() - start_time,
                    parameters=parameters
                )
                
            except Exception as e:
                error_msg = f"Tool '{tool_name}' execution failed: {e}"
                logger.error(f"Execution failed: {error_msg}", exc_info=True)
                
                # Record failure in circuit breaker
                self._record_failure(tool_key)
                
                return MCPToolResult(
                    tool_name=tool_name,
                    server_name=tool_info.server_name,
                    status=ToolExecutionStatus.FAILED,
                    error=error_msg,
                    execution_time=time.time() - start_time,
                    parameters=parameters
                )
            
        except Exception as e:
            error_msg = f"Unexpected error executing tool '{tool_name}': {e}"
            logger.error(f"Unexpected error: {error_msg}", exc_info=True)
            return MCPToolResult(
                tool_name=tool_name,
                server_name=server_name or "unknown",
                status=ToolExecutionStatus.SERVER_ERROR,
                error=error_msg,
                execution_time=time.time() - start_time,
                parameters=parameters
            )
    
    def _validate_parameters(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> 'ValidationResult':
        """Validate parameters against tool schema using JSON Schema"""
        try:
            # Check if schema is valid
            if not isinstance(schema, dict):
                return ValidationResult(False, "Invalid schema format")
            
            # Validate parameters against schema
            validate(instance=parameters, schema=schema)
            
            return ValidationResult(True, None)
            
        except ValidationError as e:
            # Extract meaningful error message
            error_path = ' -> '.join(str(p) for p in e.path) if e.path else 'root'
            error_msg = f"Validation error at {error_path}: {e.message}"
            return ValidationResult(False, error_msg)
            
        except Exception as e:
            return ValidationResult(False, f"Schema validation error: {e}")
    
    def _process_tool_result(self, result: Any) -> Any:
        """Process tool execution result"""
        try:
            # Handle different result types
            if hasattr(result, 'content'):
                # MCP ToolResult with content
                content = result.content
                if isinstance(content, list) and len(content) > 0:
                    # Extract text content
                    text_content = []
                    for item in content:
                        if hasattr(item, 'text'):
                            text_content.append(item.text)
                        elif hasattr(item, 'content'):
                            text_content.append(str(item.content))
                        else:
                            text_content.append(str(item))
                    
                    # Return combined text or JSON if it looks like JSON
                    combined_text = '\n'.join(text_content)
                    try:
                        return json.loads(combined_text)
                    except json.JSONDecodeError:
                        return combined_text
                else:
                    return str(content)
            
            elif hasattr(result, 'result'):
                # Simple result object
                return result.result
                
            elif isinstance(result, (str, int, float, bool, list, dict)):
                # Direct primitive result
                return result
                
            else:
                # Convert to string as fallback
                return str(result)
                
        except Exception as e:
            logger.warning("Error processing tool result: %s", e)
            return str(result)
    
    async def execute_tools_batch(
        self, 
        tool_requests: List[Dict[str, Any]]
    ) -> List[MCPToolResult]:
        """
        Execute multiple tools in batch
        
        Args:
            tool_requests: List of tool requests with 'tool_name', 'parameters', and optional 'server_name'
            
        Returns:
            List of MCPToolResult objects
        """
        if not self._initialized:
            await self.initialize()
        
        logger.info("Executing batch of %d tools", len(tool_requests))
        
        # Create tasks for concurrent execution
        tasks = []
        for request in tool_requests:
            task = asyncio.create_task(
                self.execute_tool(
                    tool_name=request['tool_name'],
                    parameters=request.get('parameters', {}),
                    server_name=request.get('server_name')
                )
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle task exception
                request = tool_requests[i]
                error_result = MCPToolResult(
                    tool_name=request['tool_name'],
                    server_name=request.get('server_name', 'unknown'),
                    status=ToolExecutionStatus.SERVER_ERROR,
                    error=str(result),
                    parameters=request.get('parameters', {})
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        successful_count = sum(1 for r in processed_results if r.status == ToolExecutionStatus.SUCCESS)
        logger.info("Batch execution completed: %d/%d tools successful", successful_count, len(tool_requests))
        
        return processed_results
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return mcp_tool_registry.get_tool_names()
    
    def get_tool_info(self, tool_name: str, server_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get detailed information about a tool"""
        tool_info = mcp_tool_registry.get_tool(tool_name, server_name)
        if not tool_info:
            return None
        
        return {
            'name': tool_info.name,
            'server_name': tool_info.server_name,
            'description': tool_info.description,
            'status': tool_info.status.value,
            'schema': tool_info.schema,
            'input_schema': tool_info.input_schema,
            'last_discovered': tool_info.last_discovered,
            'capabilities': list(tool_info.capabilities)
        }
    
    def get_tools_by_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Get all tools available on a specific server"""
        tools = mcp_tool_registry.get_tools_by_server(server_name)
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'schema': tool.schema,
                'status': tool.status.value
            }
            for tool in tools
        ]
    
    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """Search for tools by name or description"""
        matching_tools = mcp_tool_registry.search_tools(query)
        return [
            {
                'name': tool.name,
                'server_name': tool.server_name,
                'description': tool.description,
                'schema': tool.schema,
                'status': tool.status.value
            }
            for tool in matching_tools
        ]
    
    async def cleanup(self) -> None:
        """Cleanup tool processor and clear cache"""
        logger.info("Cleaning up MCP Tool Processor")
        
        async with self._lock:
            self._execution_cache.clear()
            self._schema_cache.clear()
            self._circuit_breakers.clear()
        
        self._initialized = False
        logger.info("MCP Tool Processor cleanup completed")


@dataclass
class ValidationResult:
    """Result of parameter validation"""
    is_valid: bool
    error: Optional[str] = None


# Global instance
mcp_tool_processor = MCPToolProcessor()