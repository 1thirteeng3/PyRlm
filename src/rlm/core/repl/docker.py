"""
Docker Sandbox for secure code execution (v2.1 Clean Boot).

This module provides a hardened Docker container environment for executing
untrusted Python code. Uses volume mounting instead of string injection
for cleaner, more maintainable code.

Security Model:
- gVisor runtime (runsc) REQUIRED by default (fail-closed)
- Network isolation (network_mode="none")
- Resource limits (memory, CPU, PIDs)
- Read-only volume mounting for agent_lib and context
- No privilege escalation
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import docker
from docker.errors import ContainerError, DockerException, ImageNotFound

from rlm.config.settings import settings
from rlm.core.exceptions import SandboxError, SecurityViolationError

logger = logging.getLogger(__name__)

# Path to the agent_lib module (for volume mounting)
AGENT_LIB_PATH = Path(__file__).parent.parent.parent / "agent_lib"


@dataclass
class ExecutionResult:
    """Result of code execution in the sandbox."""

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False
    oom_killed: bool = False
    execution_time_ms: int = 0

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.exit_code == 0 and not self.timed_out and not self.oom_killed


@dataclass
class SandboxConfig:
    """Configuration for Docker sandbox."""

    image: str = field(default_factory=lambda: settings.docker_image)
    timeout: int = field(default_factory=lambda: settings.execution_timeout)
    memory_limit: str = field(default_factory=lambda: settings.memory_limit)
    cpu_limit: float = field(default_factory=lambda: settings.cpu_limit)
    pids_limit: int = field(default_factory=lambda: settings.pids_limit)
    network_enabled: bool = field(default_factory=lambda: settings.network_enabled)
    runtime: str = field(default_factory=lambda: settings.docker_runtime)
    # v2.1: Fail-closed security - require gVisor by default
    allow_unsafe_runtime: bool = False


class DockerSandbox:
    """
    Hardened Docker sandbox for executing untrusted Python code.

    v2.1 Changes:
    - Clean Boot: agent_lib mounted as volume instead of string injection
    - Fail-Closed: Raises error if gVisor unavailable (unless explicitly allowed)
    - No ImportBlocker: Relies on OS-level isolation only

    Security features:
    - gVisor runtime (runsc) - REQUIRED by default
    - Network isolation (network_mode="none")
    - Memory limits to prevent OOM attacks
    - Process limits to prevent fork bombs
    - CPU quotas to prevent crypto mining
    - Privilege escalation prevention
    - Read-only context mounting

    Example:
        >>> sandbox = DockerSandbox()
        >>> result = sandbox.execute("print('Hello, World!')")
        >>> print(result.stdout)
        Hello, World!
    """

    def __init__(
        self,
        image: Optional[str] = None,
        timeout: Optional[int] = None,
        config: Optional[SandboxConfig] = None,
    ) -> None:
        """
        Initialize the Docker sandbox.

        Args:
            image: Docker image to use (default: from settings)
            timeout: Execution timeout in seconds (default: from settings)
            config: Full sandbox configuration (overrides individual params)
        """
        self.config = config or SandboxConfig()
        if image:
            self.config.image = image
        if timeout:
            self.config.timeout = timeout

        self._client: Optional[docker.DockerClient] = None
        self._runtime: Optional[str] = None

    @property
    def client(self) -> docker.DockerClient:
        """Lazy-load Docker client."""
        if self._client is None:
            try:
                self._client = docker.from_env()
                # Verify Docker is accessible
                self._client.ping()
            except DockerException as e:
                raise SandboxError(
                    message="Failed to connect to Docker daemon",
                    details={"error": str(e)},
                ) from e
        return self._client

    @property
    def runtime(self) -> str:
        """Detect and cache the best available runtime."""
        if self._runtime is None:
            self._runtime = self._detect_runtime()
        return self._runtime

    def _detect_runtime(self) -> str:
        """
        Detect the most secure available Docker runtime.

        v2.1: Fail-closed - raises error if gVisor not available
        unless allow_unsafe_runtime is set.

        Returns:
            Runtime name to use.

        Raises:
            SecurityViolationError: If gVisor not found and unsafe not allowed.
        """
        if self.config.runtime != "auto":
            logger.info(f"Using configured runtime: {self.config.runtime}")
            return self.config.runtime

        try:
            info = self.client.info()
            runtimes = info.get("Runtimes", {})

            if "runsc" in runtimes:
                logger.info("✓ Secure runtime 'runsc' (gVisor) detected and enabled.")
                return "runsc"
            else:
                # v2.1: Fail-closed security
                if self.config.allow_unsafe_runtime:
                    logger.warning(
                        "⚠ SECURITY WARNING: gVisor (runsc) not found! "
                        "Using standard 'runc' isolation. "
                        "This is explicitly allowed but NOT RECOMMENDED for production."
                    )
                    return "runc"
                else:
                    raise SecurityViolationError(
                        "gVisor (runsc) not found! Execution aborted for security. "
                        "Install gVisor or set RLM_ALLOW_UNSAFE_RUNTIME=1 to allow "
                        "execution with reduced isolation (NOT RECOMMENDED).",
                        details={"available_runtimes": list(runtimes.keys())},
                    )

        except SecurityViolationError:
            raise
        except Exception as e:
            logger.error(f"Failed to detect Docker runtimes: {e}")
            if self.config.allow_unsafe_runtime:
                return "runc"
            raise SecurityViolationError(
                f"Failed to verify secure runtime: {e}",
                details={"error": str(e)},
            ) from e

    def _ensure_image(self) -> None:
        """Pull the Docker image if not available locally."""
        try:
            self.client.images.get(self.config.image)
        except ImageNotFound:
            logger.info(f"Pulling Docker image: {self.config.image}")
            self.client.images.pull(self.config.image)

    def execute(
        self,
        code: str,
        context_mount: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute Python code in a secure Docker container.

        Args:
            code: Python code to execute
            context_mount: Optional path to context file to mount read-only

        Returns:
            ExecutionResult with stdout, stderr, and exit code

        Raises:
            SandboxError: If container execution fails
            SecurityViolationError: If security configuration is invalid
        """
        self._ensure_image()

        # Write user code to temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(code)
            script_path = f.name

        try:
            # Configure volumes - CLEAN BOOT: mount agent_lib as volume
            volumes = {
                # Mount agent_lib as read-only Python package
                str(AGENT_LIB_PATH): {"bind": "/opt/rlm_agent_lib", "mode": "ro"},
                # Mount user script
                script_path: {"bind": "/tmp/user_code.py", "mode": "ro"},
            }

            if context_mount:
                volumes[context_mount] = {"bind": "/mnt/context", "mode": "ro"}

            # Configure network
            network_mode = "bridge" if self.config.network_enabled else "none"
            if self.config.network_enabled:
                logger.warning("⚠ Network access enabled - this is a security risk!")

            # Security options
            security_opt = ["no-new-privileges:true"]

            # CPU configuration (nano_cpus = 10^9 * cores)
            nano_cpus = int(self.config.cpu_limit * 1_000_000_000)

            logger.debug(
                f"Executing code in sandbox (runtime={self.runtime}, "
                f"network={network_mode}, mem={self.config.memory_limit})"
            )

            # Build the boot command
            # Sets PYTHONPATH to include mounted agent_lib, then runs boot.py
            command = [
                "sh", "-c",
                "export PYTHONPATH=/opt:$PYTHONPATH && "
                "python3 -c \""
                "import sys; sys.path.insert(0, '/opt'); "
                "from rlm_agent_lib.boot import setup_environment, execute_code; "
                "env = setup_environment(); "
                "code = open('/tmp/user_code.py').read(); "
                "execute_code(code, env)"
                "\""
            ]

            # Run the container
            container = self.client.containers.run(
                image=self.config.image,
                command=command,
                detach=True,
                # Security: Runtime
                runtime=self.runtime,
                # Security: Network isolation
                network_mode=network_mode,
                # Security: Resource limits
                mem_limit=self.config.memory_limit,
                memswap_limit=self.config.memory_limit,  # Disable swap
                nano_cpus=nano_cpus,
                pids_limit=self.config.pids_limit,
                # Security: Privileges
                security_opt=security_opt,
                # Security: IPC isolation
                ipc_mode="none",
                # IO: Volumes
                volumes=volumes,
                # Environment
                environment={
                    "PYTHONPATH": "/opt",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                # Cleanup
                remove=False,  # We need to inspect exit status first
            )

            try:
                # Wait for completion with timeout
                result = container.wait(timeout=self.config.timeout)
                exit_code = result.get("StatusCode", -1)
                timed_out = False
            except Exception:
                # Timeout or other error
                logger.warning("Container execution timed out, killing...")
                container.kill()
                exit_code = 124  # Standard timeout exit code
                timed_out = True

            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

            # Check for OOM
            container.reload()
            oom_killed = container.attrs.get("State", {}).get("OOMKilled", False)

            # Cleanup
            container.remove(force=True)

            # Truncate output for safety
            max_bytes = settings.max_stdout_bytes
            if len(stdout) > max_bytes:
                head = stdout[:1000]
                tail = stdout[-3000:]
                truncated = len(stdout) - max_bytes
                stdout = f"{head}\n... [TRUNCATED {truncated} bytes] ...\n{tail}"

            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                timed_out=timed_out,
                oom_killed=oom_killed,
            )

        except ContainerError as e:
            raise SandboxError(
                message="Container execution failed",
                exit_code=e.exit_status,
                stderr=str(e.stderr),
            ) from e

        except DockerException as e:
            raise SandboxError(
                message="Docker error during execution",
                details={"error": str(e)},
            ) from e

        finally:
            # Cleanup temp file
            Path(script_path).unlink(missing_ok=True)

    async def execute_async(
        self,
        code: str,
        context_mount: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute Python code asynchronously.

        This runs the synchronous execute() in a thread pool to avoid
        blocking the event loop. For true async Docker, use aiodocker.

        Args:
            code: Python code to execute
            context_mount: Optional path to context file

        Returns:
            ExecutionResult with stdout, stderr, and exit code
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.execute(code, context_mount),
        )

    def validate_security(self) -> dict:
        """
        Validate the security configuration.

        Returns:
            Dictionary with security checks and their status.
        """
        checks = {
            "docker_available": False,
            "gvisor_available": False,
            "gvisor_required": not self.config.allow_unsafe_runtime,
            "network_disabled": not self.config.network_enabled,
            "memory_limited": bool(self.config.memory_limit),
            "pids_limited": self.config.pids_limit < 100,
            "agent_lib_available": AGENT_LIB_PATH.exists(),
        }

        try:
            self.client.ping()
            checks["docker_available"] = True

            info = self.client.info()
            runtimes = info.get("Runtimes", {})
            checks["gvisor_available"] = "runsc" in runtimes
        except Exception:
            pass

        # Overall security status
        checks["secure"] = (
            checks["docker_available"]
            and (checks["gvisor_available"] or self.config.allow_unsafe_runtime)
            and checks["network_disabled"]
            and checks["memory_limited"]
            and checks["agent_lib_available"]
        )

        return checks
