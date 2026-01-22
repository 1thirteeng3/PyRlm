"""
RLM Agent Library - Code that runs inside the sandbox container.

This module is mounted as a read-only volume in the Docker container
and provides utilities for the agent to interact with context and data.
"""

from rlm.agent_lib.context import ContextHandle
from rlm.agent_lib.utils import llm_query

__all__ = ["ContextHandle", "llm_query"]
