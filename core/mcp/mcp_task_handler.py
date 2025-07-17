"""
MCP Task Handler for GenPod AI Backend

This module provides a high-level interface for executing tasks using MCP tools
through LLM-driven tool selection and parameter mapping. It automates the process
of selecting appropriate tools and mapping context to parameters.
"""

import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

from langchain_core.prompts import PromptTemplate
from core.prompt.prompt import Prompt
from core.prompt.prompt_template_adapters.langchain_templates.prompt_template_adapter import PromptTemplateAdapter
from core.decorators.singleton import singleton
from core.mcp.mcp_manager import mcp_manager
from core.mcp.tool_processor import ToolExecutionStatus
from llms.llm import LLM
from utils.logger import logger
from utils.yaml_utils import read_yaml


@dataclass
class TaskResult:
    """Result of task execution"""
    success: bool
    result: Any
    tool_used: str
    execution_time: float
    error: Optional[str] = None


@singleton
class MCPTaskHandler:
    """
    MCP Task Handler - High-level task execution with LLM-driven tool selection
    
    This class provides automated task execution by:
    1. Using LLM to select the most appropriate tool for a given task
    2. Mapping context data to tool parameters using LLM
    3. Executing the selected tool with mapped parameters
    
    All prompts are loaded from YAML configuration files.
    """
    
    def __init__(self):
        self._prompts = self._load_prompts()
        self._tool_selection_prompt = self._create_tool_selection_prompt()
        self._parameter_mapping_prompt = self._create_parameter_mapping_prompt()
    
    def _load_prompts(self) -> Dict[str, Any]:
        """Load prompts from YAML file"""
        try:
            return read_yaml("prompts/mcp_task_handler_prompts.yaml")
        except Exception as e:
            logger.error(f"Failed to load MCP task handler prompts: {e}")
            return {}
    
    def _create_tool_selection_prompt(self) -> Prompt:
        """Create tool selection prompt from YAML"""
        template = self._prompts.get('tool_selection_prompt_template', {}).get('template', '')
        
        if not template:
            logger.warning("Tool selection prompt template not found, using default")
            template = "Task: {task}\nAvailable Tools: {available_tools}\nReturn ONLY the tool name."
        
        langchain_template = PromptTemplate(
            template=template,
            input_variables=['task', 'available_tools']
        )
        
        adapter = PromptTemplateAdapter(langchain_template)
        return Prompt(adapter=adapter)
    
    def _create_parameter_mapping_prompt(self) -> Prompt:
        """Create parameter mapping prompt from YAML"""
        template = self._prompts.get('parameter_mapping_prompt_template', {}).get('template', '')
        
        if not template:
            logger.warning("Parameter mapping prompt template not found, using default")
            template = """Task: {task}
Tool: {tool_name}
Required Parameters: {tool_schema}
Available Context: {context}
Return JSON parameter mapping."""
        
        langchain_template = PromptTemplate(
            template=template,
            input_variables=['task', 'tool_name', 'tool_description', 'tool_schema', 'context']
        )
        
        adapter = PromptTemplateAdapter(langchain_template)
        return Prompt(adapter=adapter)
    
    async def execute_task(self, task: str, context: Dict[str, Any], llm: LLM) -> TaskResult:
        """
        Execute task using LLM-driven tool selection and parameter mapping
        
        Args:
            task: Description of the task to execute
            context: Context data available for parameter mapping
            llm: LLM instance to use for tool selection and parameter mapping
            
        Returns:
            TaskResult containing execution results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting MCP task execution: {task}")
            logger.debug(f"Context keys available: {list(context.keys())}")
            
            # Step 1: Select tool using LLM
            logger.debug("Step 1: Selecting best tool for task")
            selected_tool = await self._select_best_tool(task, llm)
            logger.info(f"Selected tool: {selected_tool}")
            
            # Step 2: Prepare parameters using LLM
            logger.debug("Step 2: Mapping context to tool parameters")
            parameters = await self._prepare_tool_parameters(task, context, selected_tool, llm)
            logger.info(f"Mapped parameters: {list(parameters.keys()) if parameters else 'None'}")
            logger.debug(f"Parameter values: {parameters}")
            
            # Step 3: Execute tool
            logger.debug("Step 3: Executing selected tool")
            result = await mcp_manager.execute_tool(selected_tool, parameters)
            
            total_time = time.time() - start_time
            
            if result.status == ToolExecutionStatus.SUCCESS:
                logger.info(f"Task executed successfully in {total_time:.2f}s using tool: {selected_tool}")
            else:
                logger.warning(f"Task execution failed in {total_time:.2f}s - Status: {result.status.value}, Error: {result.error}")
            
            return TaskResult(
                success=result.status == ToolExecutionStatus.SUCCESS,
                result=result.result,
                tool_used=selected_tool,
                execution_time=result.execution_time,
                error=result.error
            )
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Task execution failed after {total_time:.2f}s: {e}", exc_info=True)
            return TaskResult(
                success=False,
                result=None,
                tool_used="unknown",
                execution_time=total_time,
                error=str(e)
            )
    
    async def _select_best_tool(self, task: str, llm: LLM) -> str:
        """Select best tool using LLM and YAML prompt"""
        try:
            logger.debug("Getting available tools from MCP manager")
            
            # Get available tools with descriptions
            available_tools = []
            tool_names = mcp_manager.get_available_tools()
            logger.debug(f"Found {len(tool_names)} available tools")
            
            for tool_name in tool_names:
                tool_info = mcp_manager.get_tool_info(tool_name)
                available_tools.append({
                    'name': tool_name,
                    'description': tool_info.get('description', 'No description available')
                })
                logger.debug(f"Tool: {tool_name} - {tool_info.get('description', 'No description')}")
            
            if not available_tools:
                raise ValueError("No MCP tools available")
            
            logger.debug("Using LLM to select best tool")
            
            # Use LLM to select tool
            prompt_inputs = {
                'task': task,
                'available_tools': json.dumps(available_tools, indent=2)
            }
            
            llm_output = llm.invoke(
                prompt=self._tool_selection_prompt,
                prompt_inputs=prompt_inputs,
                response_type='string'
            )
            
            selected_tool = llm_output.response.strip()
            logger.debug(f"LLM selected tool: {selected_tool}")
            
            # Validate selected tool exists
            available_tool_names = [tool['name'] for tool in available_tools]
            if selected_tool not in available_tool_names:
                logger.warning(f"Selected tool '{selected_tool}' not in available tools. Using first available tool.")
                selected_tool = available_tool_names[0]
                logger.debug(f"Fallback to first available tool: {selected_tool}")
            
            return selected_tool
            
        except Exception as e:
            logger.error(f"Tool selection failed: {e}", exc_info=True)
            raise ValueError(f"Failed to select tool: {e}")
    
    async def _prepare_tool_parameters(self, task: str, context: Dict[str, Any], tool_name: str, llm: LLM) -> Dict[str, Any]:
        """Prepare parameters using LLM and YAML prompt"""
        try:
            logger.debug(f"Getting tool info for: {tool_name}")
            
            # Get tool information
            tool_info = mcp_manager.get_tool_info(tool_name)
            if not tool_info:
                logger.warning(f"No tool info found for {tool_name}")
                return {}
            
            tool_schema = tool_info.get('schema', {}).get('properties', {})
            logger.debug(f"Tool schema parameters: {list(tool_schema.keys())}")
            
            # If no schema or context, return empty parameters
            if not tool_schema or not context:
                logger.info(f"No schema or context for tool {tool_name}, returning empty parameters")
                return {}
            
            logger.debug("Using LLM to map context to tool parameters")
            
            # Use LLM to map parameters
            prompt_inputs = {
                'task': task,
                'tool_name': tool_name,
                'tool_description': tool_info.get('description', ''),
                'tool_schema': json.dumps(tool_schema, indent=2),
                'context': json.dumps(context, indent=2)
            }
            
            llm_output = llm.invoke(
                prompt=self._parameter_mapping_prompt,
                prompt_inputs=prompt_inputs,
                response_type='string'
            )
            
            logger.debug(f"LLM parameter mapping response: {llm_output.response}")
            
            # Parse LLM response as JSON
            try:
                parameters = json.loads(llm_output.response)
                logger.debug(f"Parsed parameters: {parameters}")
                
                # Validate parameters against schema
                validated_params = {}
                for param_name, param_value in parameters.items():
                    if param_name in tool_schema:
                        validated_params[param_name] = param_value
                        logger.debug(f"Validated parameter: {param_name} = {param_value}")
                    else:
                        logger.warning(f"Parameter '{param_name}' not in tool schema, skipping")
                
                logger.debug(f"Final validated parameters: {validated_params}")
                return validated_params
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse parameter mapping as JSON: {llm_output.response}")
                logger.error(f"JSON decode error: {e}")
                return {}
            
        except Exception as e:
            logger.error(f"Parameter preparation failed: {e}", exc_info=True)
            return {}


# Global instance
mcp_task_handler = MCPTaskHandler()