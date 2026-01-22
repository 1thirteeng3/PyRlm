# Configuration

RLM-Python is configured via environment variables.

## All Settings

| Variable | Default | Description |
|----------|---------|-------------|
| **Docker** |||
| `RLM_DOCKER_IMAGE` | `python:3.11-slim` | Container image for execution |
| `RLM_DOCKER_RUNTIME` | `auto` | Runtime: `auto`, `runsc`, or `runc` |
| `RLM_ALLOW_UNSAFE_RUNTIME` | `0` | Allow execution without gVisor |
| **Limits** |||
| `RLM_MEMORY_LIMIT` | `256m` | Memory limit per container |
| `RLM_CPU_LIMIT` | `0.5` | CPU cores (fractional allowed) |
| `RLM_PIDS_LIMIT` | `50` | Max processes in container |
| `RLM_EXECUTION_TIMEOUT` | `30` | Timeout in seconds |
| **Network** |||
| `RLM_NETWORK_ENABLED` | `0` | Allow network access (risky!) |
| **Egress Filtering** |||
| `RLM_ENTROPY_THRESHOLD` | `4.5` | Shannon entropy for secrets |
| `RLM_SIMILARITY_THRESHOLD` | `0.8` | Context echo detection |
| `RLM_MAX_STDOUT_BYTES` | `4000` | Output truncation limit |
| **LLM** |||
| `RLM_LLM_PROVIDER` | `openai` | Provider: openai, anthropic, google |
| `RLM_LLM_MODEL` | `gpt-4` | Model name |
| `RLM_MAX_RECURSION_DEPTH` | `10` | Max LLM iterations |
| **Budget** |||
| `RLM_MAX_BUDGET_DOLLARS` | `1.0` | Maximum spend per run |

## Configuration via Code

```python
from rlm import Orchestrator
from rlm.core.repl import SandboxConfig
from rlm.core import OrchestratorConfig

# Sandbox configuration
sandbox_config = SandboxConfig(
    image="python:3.11-slim",
    timeout=60,
    memory_limit="512m",
    cpu_limit=1.0,
    network_enabled=False,
    allow_unsafe_runtime=False,  # Require gVisor
)

# Orchestrator configuration
orch_config = OrchestratorConfig(
    max_iterations=15,
    raise_on_leak=True,  # Raise exception instead of redacting
)

# Create with custom configs
agent = Orchestrator(config=orch_config)
```

## Security Configurations

### Production (Maximum Security)

```bash
export RLM_DOCKER_RUNTIME=runsc  # Force gVisor
export RLM_NETWORK_ENABLED=0     # Block network
export RLM_MEMORY_LIMIT=128m     # Tight limits
export RLM_EXECUTION_TIMEOUT=15  # Short timeout
```

### Development (Relaxed)

```bash
export RLM_ALLOW_UNSAFE_RUNTIME=1  # Allow without gVisor
export RLM_EXECUTION_TIMEOUT=120   # Longer timeout
export RLM_MEMORY_LIMIT=512m       # More resources
```

!!! warning "Never in Production"
    Never use `RLM_ALLOW_UNSAFE_RUNTIME=1` in production environments.

## Custom Docker Images

To use additional Python packages, create a custom image:

```dockerfile
FROM python:3.11-slim

# Install your dependencies
RUN pip install numpy pandas scikit-learn matplotlib

# Keep the image small
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
```

Build and use:

```bash
docker build -t my-rlm-image:latest .
export RLM_DOCKER_IMAGE=my-rlm-image:latest
```
