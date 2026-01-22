# Docker Sandbox

::: rlm.core.repl.docker.DockerSandbox
    handler: python
    options:
      members:
        - __init__
        - execute
        - execute_async
        - validate_security
      show_root_full_path: false
      show_source: true

## Sandbox Configuration

::: rlm.core.repl.docker.SandboxConfig
    handler: python
    options:
      show_root_full_path: false

## Execution Result

::: rlm.core.repl.docker.ExecutionResult
    handler: python
    options:
      show_root_full_path: false

## Async Sandbox

For true async Docker operations, use `AsyncDockerSandbox`:

::: rlm.core.repl.async_docker.AsyncDockerSandbox
    handler: python
    options:
      members:
        - __init__
        - execute
      show_root_full_path: false

## Direct Usage

```python
from rlm.core.repl import DockerSandbox, SandboxConfig

# Custom configuration
config = SandboxConfig(
    image="python:3.11-slim",
    timeout=60,
    memory_limit="512m",
    allow_unsafe_runtime=False,  # Require gVisor
)

sandbox = DockerSandbox(config=config)

# Execute code
result = sandbox.execute("print('Hello from sandbox!')")
print(result.stdout)
```

## Security Validation

```python
checks = sandbox.validate_security()

print(f"Docker available: {checks['docker_available']}")
print(f"gVisor available: {checks['gvisor_available']}")
print(f"Network disabled: {checks['network_disabled']}")
print(f"Overall secure: {checks['secure']}")
```
