# Orchestrator

::: rlm.core.orchestrator.Orchestrator
    handler: python
    options:
      members:
        - __init__
        - run
        - arun
        - chat
      show_root_full_path: false
      show_source: true

## Usage Examples

### Basic Async

```python
import asyncio
from rlm import Orchestrator

async def main():
    agent = Orchestrator()
    result = await agent.arun("Calculate sqrt(144)")
    print(result.final_answer)

asyncio.run(main())
```

### With Custom Configuration

```python
from rlm import Orchestrator
from rlm.core import OrchestratorConfig

config = OrchestratorConfig(
    max_iterations=5,
    raise_on_leak=True,
)

agent = Orchestrator(config=config)
result = agent.run("What is 2+2?")
```

### With Context File

```python
result = await agent.arun(
    query="Summarize this document",
    context_path="/path/to/document.txt"
)
```

## Result Object

::: rlm.core.orchestrator.OrchestratorResult
    handler: python
    options:
      show_root_full_path: false

## Configuration

::: rlm.core.orchestrator.OrchestratorConfig
    handler: python
    options:
      show_root_full_path: false
