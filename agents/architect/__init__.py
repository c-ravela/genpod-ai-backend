"""
Architect Agent Module

This module provides the implementation of the Architect agent, a specialized Project Manager agent 
responsible for transforming user input into comprehensive documentation for team members.

Key responsibilities include:
  - Crafting precise and clear project requirements.
  - Determining the optimal folder structure for project organization.
  - Generating a detailed list of tasks necessary for project completion.

The module exposes the following components:
  - ArchitectAgent: The main agent class responsible for orchestrating the documentation generation process.
  - ArchitectGraph: The graph representation that models the agent's workflow and execution steps.
  - ArchitectState, ArchitectInput, ArchitectOutput: Data models for managing the state and inputs/outputs of the agent.
  - ArchitectWorkFlow: The workflow logic that drives the agent's decision-making process.

These components work together to ensure that the Architect agent can effectively translate user requests 
into actionable project documentation, following best practices in microservice architecture, project organization,
and clean-code development.
"""

from ._internal.architect_graph import ArchitectGraph
from ._internal.architect_state import *
from ._internal.architect_work_flow import ArchitectWorkFlow
from .architect_agent import ArchitectAgent

__all__ = [
    "ArchitectAgent",
    "ArchitectGraph",
    "ArchitectInput",
    "ArchitectOutput",
    "ArchitectState",
    "ArchitectWorkFlow"
]
