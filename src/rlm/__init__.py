"""
RLM - Recursive Language Model

A secure LLM-driven code execution library with Docker sandboxing,
egress filtering, and memory-efficient context handling.
"""

from rlm.config.settings import settings
from rlm.core.exceptions import (
    BudgetExceededError,
    ContextError,
    DataLeakageError,
    RLMError,
    SandboxError,
    SecurityViolationError,
)
from rlm.core.memory.handle import ContextHandle
from rlm.core.orchestrator import Orchestrator
from rlm.core.repl.docker import DockerSandbox

__version__ = "2.0.0"
__all__ = [
    # Core classes
    "Orchestrator",
    "DockerSandbox",
    "ContextHandle",
    # Configuration
    "settings",
    # Exceptions
    "RLMError",
    "SecurityViolationError",
    "DataLeakageError",
    "BudgetExceededError",
    "SandboxError",
    "ContextError",
]
