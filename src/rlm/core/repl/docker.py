"""
Docker Sandbox for secure code execution.

This module provides a hardened Docker container environment for executing
untrusted Python code with maximum isolation (gVisor, network isolation,
resource limits, privilege restrictions).
"""

import logging
import shlex
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import docker
from docker.errors import ContainerError, DockerException, ImageNotFound

from rlm.config.settings import settings
from rlm.core.exceptions import SandboxError, SecurityViolationError

logger = logging.getLogger(__name__)


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


class DockerSandbox:
    """
    Hardened Docker sandbox for executing untrusted Python code.

    Security features:
    - gVisor runtime (runsc) when available
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

        Preference order:
        1. runsc (gVisor) - Best isolation
        2. runc with seccomp - Standard isolation

        Returns:
            Runtime name to use.
        """
        if self.config.runtime != "auto":
            logger.info(f"Using configured runtime: {self.config.runtime}")
            return self.config.runtime

        try:
            info = self.client.info()
            runtimes = info.get("Runtimes", {})

            if "runsc" in runtimes:
                logger.info("✓ Runtime seguro 'runsc' (gVisor) detectado e ativado.")
                return "runsc"
            else:
                logger.warning(
                    "⚠ AVISO DE SEGURANÇA: 'runsc' não encontrado. "
                    "Usando isolamento padrão 'runc'."
                )
                return "runc"

        except Exception as e:
            logger.error(f"Falha ao detectar runtimes Docker: {e}")
            return "runc"

    def _ensure_image(self) -> None:
        """Pull the Docker image if not available locally."""
        try:
            self.client.images.get(self.config.image)
        except ImageNotFound:
            logger.info(f"Pulling Docker image: {self.config.image}")
            self.client.images.pull(self.config.image)

    def _build_execution_script(self, code: str, context_path: Optional[str] = None) -> str:
        """
        Build the Python script to execute inside the container.

        This injects the ContextHandle class and any necessary setup code.
        """
        setup_code = '''
import sys
import os

# Disable dangerous imports
_blocked_modules = {'subprocess', 'multiprocessing', 'ctypes', 'cffi'}

class ImportBlocker:
    def find_module(self, name, path=None):
        if name in _blocked_modules or any(name.startswith(m + '.') for m in _blocked_modules):
            return self
        return None
    
    def load_module(self, name):
        raise ImportError(f"Module '{name}' is blocked for security reasons")

sys.meta_path.insert(0, ImportBlocker())
'''

        context_setup = ""
        if context_path:
            context_setup = f'''
# Context Handle for memory-efficient file access
class ContextHandle:
    def __init__(self, path="/mnt/context"):
        self.path = path
        if not os.path.exists(path):
            raise FileNotFoundError(f"Context file not found at {{path}}")
        self._size = os.path.getsize(path)
    
    @property
    def size(self):
        return self._size
    
    def read_window(self, offset, radius=500):
        start = max(0, offset - radius)
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(start)
            return f.read(radius * 2)
    
    def snippet(self, offset, window=500):
        return self.read_window(offset, window // 2)
    
    def search(self, pattern, max_results=10):
        import re
        matches = []
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                for m in re.finditer(pattern, line):
                    matches.append((i, m.group()))
                    if len(matches) >= max_results:
                        return matches
        return matches

ctx = ContextHandle()
'''

        return f"{setup_code}\n{context_setup}\n# User code starts here\n{code}"

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

        # Build the full script with security setup
        full_script = self._build_execution_script(code, context_mount)

        # Create a temporary file with the script
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(full_script)
            script_path = f.name

        try:
            # Configure volumes
            volumes = {
                script_path: {"bind": "/tmp/script.py", "mode": "ro"},
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

            # Run the container
            container = self.client.containers.run(
                image=self.config.image,
                command=["python3", "/tmp/script.py"],
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

    def validate_security(self) -> dict:
        """
        Validate the security configuration.

        Returns:
            Dictionary with security checks and their status.
        """
        checks = {
            "docker_available": False,
            "gvisor_available": False,
            "network_disabled": not self.config.network_enabled,
            "memory_limited": bool(self.config.memory_limit),
            "pids_limited": self.config.pids_limit < 100,
        }

        try:
            self.client.ping()
            checks["docker_available"] = True
            checks["gvisor_available"] = self.runtime == "runsc"
        except Exception:
            pass

        return checks
