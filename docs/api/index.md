# API Reference

Complete API documentation for RLM-Python.

## Core Classes

| Class | Description |
|-------|-------------|
| [`Orchestrator`](orchestrator.md) | Main LLM agent loop |
| [`DockerSandbox`](sandbox.md) | Secure code execution |
| [`ContextHandle`](context-handle.md) | Memory-efficient file access |
| [`EgressFilter`](egress.md) | Output sanitization |

## LLM Clients

| Class | Description |
|-------|-------------|
| [`BaseLLMClient`](llm.md#basellmclient) | Abstract base class |
| [`OpenAIClient`](llm.md#openaiclient) | OpenAI GPT models |
| [`AnthropicClient`](llm.md#anthropicclient) | Anthropic Claude |
| [`GoogleClient`](llm.md#googleclient) | Google Gemini |

## Exceptions

| Exception | Description |
|-----------|-------------|
| [`RLMError`](exceptions.md#rlmerror) | Base exception |
| [`SecurityViolationError`](exceptions.md#securityviolationerror) | Security boundary violation |
| [`DataLeakageError`](exceptions.md#dataleakageerror) | Egress filter triggered |
| [`BudgetExceededError`](exceptions.md#budgetexceedederror) | Cost limit reached |
| [`SandboxError`](exceptions.md#sandboxerror) | Container execution failure |

## Utilities

| Class/Function | Description |
|----------------|-------------|
| [`BudgetManager`](../guide/budget.md) | Cost tracking |
| [`RLMSettings`](../getting-started/configuration.md) | Configuration |

## Quick Example

```python
from rlm import Orchestrator, DockerSandbox, ContextHandle

# Full orchestration
orchestrator = Orchestrator()
result = orchestrator.run("Calculate fibonacci(20)")
print(result.final_answer)

# Direct sandbox
sandbox = DockerSandbox()
exec_result = sandbox.execute("print(sum(range(100)))")
print(exec_result.stdout)

# Large file handling
with ContextHandle("/path/to/file.txt") as ctx:
    matches = ctx.search(r"pattern")
```
