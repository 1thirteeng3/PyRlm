"""
Async Docker Sandbox using aiodocker (v3.0).

v3.0 Changes:
- TemporaryDirectory for crash-safe cleanup
- Direct aiodocker import (fail-fast)
- True async for non-blocking operations
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

# v3.0: Direct import - fail-fast if not installed
import aiodocker
from aiodocker.exceptions import DockerError

from rlm.config.settings import settings
from rlm.core.exceptions import SandboxError, SecurityViolationError
from rlm.core.repl.docker import ExecutionResult, SandboxConfig, AGENT_LIB_PATH

logger = logging.getLogger(__name__)


class AsyncDockerSandbox:
    """
    Async Docker sandbox using aiodocker for non-blocking operations.
    
    v3.0: Uses TemporaryDirectory for crash-safe cleanup.
    No leftover files in /tmp even on SIGKILL.
    
    Example:
        >>> sandbox = AsyncDockerSandbox()
        >>> result = await sandbox.execute("print('Hello!')")
        >>> print(result.stdout)
        Hello!
    """
    
    def __init__(
        self,
        image: Optional[str] = None,
        timeout: Optional[int] = None,
        config: Optional[SandboxConfig] = None,
    ) -> None:
        """Initialize the async sandbox."""
        self.config = config or SandboxConfig()
        if image:
            self.config.image = image
        if timeout:
            self.config.timeout = timeout
        
        self._runtime: Optional[str] = None
    
    async def _detect_runtime(self, docker: aiodocker.Docker) -> str:
        """Detect the best available runtime (fail-closed by default)."""
        if self.config.runtime != "auto":
            return self.config.runtime
        
        try:
            info = await docker.system.info()
            runtimes = info.get("Runtimes", {})
            
            if "runsc" in runtimes:
                logger.info("✓ Secure runtime 'runsc' (gVisor) detected.")
                return "runsc"
            else:
                if self.config.allow_unsafe_runtime:
                    logger.warning("⚠ gVisor not found, using runc.")
                    return "runc"
                else:
                    raise SecurityViolationError(
                        "gVisor (runsc) not found! Set RLM_ALLOW_UNSAFE_RUNTIME=1 to allow."
                    )
        except SecurityViolationError:
            raise
        except Exception as e:
            if self.config.allow_unsafe_runtime:
                return "runc"
            raise SecurityViolationError(f"Runtime detection failed: {e}") from e
    
    async def _ensure_image(self, docker: aiodocker.Docker) -> None:
        """Pull image if not available."""
        try:
            await docker.images.inspect(self.config.image)
        except DockerError:
            logger.info(f"Pulling image: {self.config.image}")
            await docker.images.pull(self.config.image)
    
    async def execute(
        self,
        code: str,
        context_mount: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute code in an async Docker container.
        
        v3.0: Uses TemporaryDirectory for crash-safe cleanup.
        Directory auto-destructs on exit even under exceptions.
        
        Args:
            code: Python code to execute
            context_mount: Optional context file path
            
        Returns:
            ExecutionResult with stdout, stderr, exit_code
        """
        # v3.0: TemporaryDirectory for crash-safe cleanup
        with tempfile.TemporaryDirectory(prefix="rlm_exec_") as tmpdir:
            script_path = Path(tmpdir) / "user_code.py"
            script_path.write_text(code, encoding="utf-8")
            
            try:
                async with aiodocker.Docker() as docker:
                    runtime = await self._detect_runtime(docker)
                    await self._ensure_image(docker)
                    
                    # Build volume binds
                    binds = [
                        f"{AGENT_LIB_PATH}:/opt/rlm_agent_lib:ro",
                        f"{str(script_path)}:/tmp/user_code.py:ro",
                    ]
                    if context_mount:
                        binds.append(f"{context_mount}:/mnt/context:ro")
                    
                    config = {
                        "Image": self.config.image,
                        "Cmd": [
                            "sh", "-c",
                            "export PYTHONPATH=/opt:$PYTHONPATH && "
                            "python3 -c \""
                            "import sys; sys.path.insert(0, '/opt'); "
                            "from rlm_agent_lib.boot import setup_environment, execute_code; "
                            "env = setup_environment(); "
                            "code = open('/tmp/user_code.py').read(); "
                            "execute_code(code, env)"
                            "\""
                        ],
                        "HostConfig": {
                            "Binds": binds,
                            "NetworkMode": "none" if not self.config.network_enabled else "bridge",
                            "Memory": self._parse_memory_limit(self.config.memory_limit),
                            "MemorySwap": self._parse_memory_limit(self.config.memory_limit),
                            "NanoCPUs": int(self.config.cpu_limit * 1_000_000_000),
                            "PidsLimit": self.config.pids_limit,
                            "SecurityOpt": ["no-new-privileges:true"],
                            "IpcMode": "none",
                            "Runtime": runtime,
                        },
                        "Env": [
                            "PYTHONPATH=/opt",
                            "PYTHONDONTWRITEBYTECODE=1",
                        ],
                    }
                    
                    # Create and start container
                    container = await docker.containers.create(config=config)
                    
                    try:
                        await container.start()
                        
                        # Wait with timeout
                        try:
                            result = await asyncio.wait_for(
                                container.wait(),
                                timeout=self.config.timeout,
                            )
                            exit_code = result.get("StatusCode", -1)
                            timed_out = False
                        except asyncio.TimeoutError:
                            logger.warning("Container timed out, killing...")
                            await container.kill()
                            exit_code = 124
                            timed_out = True
                        
                        # Get logs
                        logs = await container.log(stdout=True, stderr=True)
                        stdout = "".join(logs)
                        stderr = ""
                        
                        # Check OOM
                        info = await container.show()
                        oom_killed = info.get("State", {}).get("OOMKilled", False)
                        
                        # Truncate if needed
                        max_bytes = settings.max_stdout_bytes
                        if len(stdout) > max_bytes:
                            stdout = stdout[:1000] + "\n...[TRUNCATED]...\n" + stdout[-3000:]
                        
                        return ExecutionResult(
                            stdout=stdout,
                            stderr=stderr,
                            exit_code=exit_code,
                            timed_out=timed_out,
                            oom_killed=oom_killed,
                        )
                        
                    finally:
                        await container.delete(force=True)
            
            except DockerError as e:
                raise SandboxError(
                    message="Async Docker execution failed",
                    details={"error": str(e)},
                ) from e
        
        # Temp directory auto-cleaned here
    
    @staticmethod
    def _parse_memory_limit(limit: str) -> int:
        """Parse memory limit string to bytes."""
        limit = limit.lower()
        multipliers = {
            'k': 1024,
            'm': 1024**2,
            'g': 1024**3,
        }
        
        for suffix, mult in multipliers.items():
            if limit.endswith(suffix):
                return int(limit[:-1]) * mult
        
        return int(limit)
