# Quick Start

Get RLM-Python running in under 2 minutes.

## Prerequisites

!!! warning "Docker Required"
    RLM executes code in Docker containers. Make sure Docker Engine is installed and running.
    
    ```bash
    docker --version  # Should show Docker version
    docker ps         # Should work without errors
    ```

## Installation

=== "pip"
    ```bash
    pip install rlm-python
    ```

=== "poetry"
    ```bash
    poetry add rlm-python
    ```

=== "uv"
    ```bash
    uv add rlm-python
    ```

## Your First Agent

### Async (Recommended)

```python
import asyncio
from rlm import Orchestrator

async def main():
    # Initialize the orchestrator
    agent = Orchestrator()
    
    # Execute a query (non-blocking)
    result = await agent.arun("What is 42 * 17?")
    
    print(f"Success: {result.success}")
    print(f"Answer: {result.final_answer}")
    print(f"Iterations: {result.iterations}")

asyncio.run(main())
```

### Synchronous

```python
from rlm import Orchestrator

agent = Orchestrator()
result = agent.run("Calculate the factorial of 10")

print(result.final_answer)  # 3628800
```

## Understanding Results

The `OrchestratorResult` contains:

| Field | Type | Description |
|-------|------|-------------|
| `final_answer` | `str` | The extracted answer from `FINAL(...)` |
| `success` | `bool` | Whether execution completed successfully |
| `iterations` | `int` | Number of LLM ↔ Code cycles |
| `steps` | `list` | Detailed execution steps |
| `budget_summary` | `dict` | Token usage and cost |

## Next Steps

- [:material-cog: Configuration](configuration.md) - Customize settings
- [:material-lightning-bolt: Async Guide](../guide/async.md) - Deep dive into async
- [:material-shield: Security](../security/architecture.md) - Understand the security model
