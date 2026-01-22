# Docker Sandbox

The `DockerSandbox` provides secure, isolated code execution in Docker containers.

## Security Features

| Feature | Default | Description |
|---------|---------|-------------|
| **gVisor Runtime** | Auto-detect | Intercepts syscalls in userspace |
| **Network Isolation** | Enabled | `network_mode="none"` |
| **Memory Limit** | 512MB | Prevents OOM attacks |
| **PID Limit** | 50 | Prevents fork bombs |
| **CPU Quota** | 1 core | Prevents crypto mining |
| **No New Privileges** | Enabled | Blocks privilege escalation |

## Basic Usage

```python
from rlm import DockerSandbox

sandbox = DockerSandbox()

result = sandbox.execute("""
print("Hello from sandbox!")
import sys
print(f"Python version: {sys.version}")
""")

print(result.stdout)
print(f"Exit code: {result.exit_code}")
print(f"Success: {result.success}")
```

## Custom Configuration

```python
from rlm.core.repl.docker import DockerSandbox, SandboxConfig

config = SandboxConfig(
    image="python:3.11-slim",
    timeout=60,
    memory_limit="1g",
    cpu_limit=2.0,
    pids_limit=100,
    network_enabled=False,
)

sandbox = DockerSandbox(config=config)
```

## Execution Result

```python
@dataclass
class ExecutionResult:
    stdout: str           # Standard output
    stderr: str           # Standard error
    exit_code: int        # Process exit code
    timed_out: bool       # True if execution timed out
    oom_killed: bool      # True if killed by OOM
    
    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and not self.oom_killed
```

## With Context Mount

Mount a file as read-only for the code to access:

```python
result = sandbox.execute(
    code="""
with open('/mnt/context', 'r') as f:
    print(f.read()[:100])
""",
    context_mount="/path/to/data.txt"
)
```

## Security Validation

```python
security = sandbox.validate_security()
print(security)
# {
#     'docker_available': True,
#     'gvisor_available': True,
#     'network_disabled': True,
#     'memory_limited': True,
#     'pids_limited': True
# }
```

## Blocked Modules

The sandbox automatically blocks dangerous modules:

- `subprocess`
- `multiprocessing`
- `ctypes`
- `cffi`

```python
# This will raise ImportError in the sandbox:
import subprocess  # Blocked!
```
