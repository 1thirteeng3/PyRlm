# Basic Usage

Learn the fundamentals of RLM-Python.

## The Agent Loop

RLM implements a **ReAct-style agent loop**:

```mermaid
graph LR
    A[Query] --> B[LLM]
    B --> C{Code?}
    C -->|Yes| D[Execute in Sandbox]
    D --> E[Filter Output]
    E --> B
    C -->|FINAL()| F[Return Answer]
```

1. **Query** → Send to LLM with system prompt
2. **LLM** → Generates Python code in markdown blocks
3. **Execute** → Run code in Docker sandbox
4. **Filter** → Apply egress filtering to output
5. **Observe** → Feed output back to LLM
6. **Repeat** until `FINAL(answer)` is returned

## Basic Example

```python
from rlm import Orchestrator

agent = Orchestrator()

# Simple query
result = agent.run("What is the square root of 144?")

print(result.final_answer)  # "12" or "12.0"
```

## Understanding Responses

```python
result = agent.run("Calculate 2^10")

# Check if successful
if result.success:
    print(f"Answer: {result.final_answer}")
else:
    print(f"Error: {result.error}")

# Inspect execution details
print(f"Iterations: {result.iterations}")
print(f"Total steps: {len(result.steps)}")

# View cost
summary = result.budget_summary
print(f"Tokens used: {summary['total_tokens']}")
print(f"Cost: ${summary['total_cost']:.4f}")
```

## Execution Steps

Each step records what happened:

```python
for step in result.steps:
    print(f"[{step.action}] Iteration {step.iteration}")
    
    if step.action == "llm_call":
        print(f"  LLM response: {step.output_data[:100]}...")
    elif step.action == "code_execution":
        print(f"  Code: {step.input_data[:100]}...")
        print(f"  Output: {step.output_data}")
    elif step.action == "final_answer":
        print(f"  Answer: {step.output_data}")
```

## Error Handling

```python
from rlm import Orchestrator
from rlm.core.exceptions import RLMError, SandboxError

agent = Orchestrator()

try:
    result = agent.run("Analyze this data")
    
    if result.success:
        print(result.final_answer)
    else:
        print(f"Agent failed: {result.error}")
        
except SandboxError as e:
    print(f"Docker error: {e}")
except RLMError as e:
    print(f"RLM error: {e}")
```

## The FINAL() Convention

The LLM signals completion with `FINAL(answer)`:

```python
# The LLM generates code like:
"""
result = calculate_something()
print(f"FINAL({result})")
"""

# RLM extracts "answer" from FINAL(answer)
```

Multiple formats are supported:

- `FINAL(42)`
- `FINAL: The answer is 42`
- `Final Answer: 42`
