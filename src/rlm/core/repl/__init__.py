"""REPL module for code execution."""

from rlm.core.repl.docker import DockerSandbox, ExecutionResult, SandboxConfig

# v2.1: Async sandbox (optional import)
try:
    from rlm.core.repl.async_docker import AsyncDockerSandbox
except ImportError:
    AsyncDockerSandbox = None  # type: ignore

__all__ = ["DockerSandbox", "ExecutionResult", "SandboxConfig", "AsyncDockerSandbox"]
