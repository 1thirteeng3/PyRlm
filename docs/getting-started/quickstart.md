# Quick Start

This guide will get you running RLM in under 5 minutes.

## Step 1: Configure API Key

Create a `.env` file in your project root:

```bash
# .env
RLM_API_KEY=sk-your-openai-key-here
RLM_API_PROVIDER=openai
```

Or set environment variables:

=== "Windows"
    ```powershell
    $env:RLM_API_KEY = "sk-your-key"
    $env:RLM_API_PROVIDER = "openai"
    ```

=== "Linux/macOS"
    ```bash
    export RLM_API_KEY="sk-your-key"
    export RLM_API_PROVIDER="openai"
    ```

## Step 2: Basic Usage

### Simple Query with Code Execution

```python
from rlm import Orchestrator

# Create orchestrator
orchestrator = Orchestrator()

# Run a query that requires computation
result = orchestrator.run("Calculate the factorial of 20")

print(result.final_answer)
# 2432902008176640000

print(f"Iterations: {result.iterations}")
print(f"Cost: ${result.budget_summary['total_spent_usd']:.4f}")
```

### Direct Sandbox Usage

For direct code execution without LLM:

```python
from rlm import DockerSandbox

sandbox = DockerSandbox()

result = sandbox.execute("""
import math

# Calculate some values
pi_value = math.pi
factorial_10 = math.factorial(10)

print(f"Pi: {pi_value}")
print(f"10!: {factorial_10}")
""")

print(result.stdout)
# Pi: 3.141592653589793
# 10!: 3628800
```

### Working with Large Files

```python
from rlm import ContextHandle

# Open a large file efficiently
with ContextHandle("/path/to/large_data.txt") as ctx:
    print(f"File size: {ctx.size_mb:.2f} MB")
    
    # Search without loading entire file
    matches = ctx.search(r"ERROR.*")
    
    for offset, match in matches[:5]:
        snippet = ctx.snippet(offset, window=200)
        print(f"Found at {offset}: {snippet[:100]}...")
```

### Query with Context

```python
from rlm import Orchestrator

orchestrator = Orchestrator()

# Query against a document
result = orchestrator.run(
    query="What are the main topics discussed in this document?",
    context_path="/path/to/document.txt"
)

print(result.final_answer)
```

## Step 3: Check Your Setup

Verify everything is working:

```python
from rlm import DockerSandbox, settings

print("=== RLM Configuration ===")
print(f"Provider: {settings.api_provider}")
print(f"Model: {settings.model_name}")
print(f"Has API Key: {settings.has_api_key}")

print("\n=== Security Check ===")
sandbox = DockerSandbox()
security = sandbox.validate_security()
for check, status in security.items():
    emoji = "✅" if status else "⚠️"
    print(f"{emoji} {check}: {status}")
```

## Next Steps

- [Configuration Reference](configuration.md) - All available options
- [Orchestrator Guide](../guide/orchestrator.md) - Advanced agent usage
- [Security Best Practices](../security/best-practices.md) - Production deployment
