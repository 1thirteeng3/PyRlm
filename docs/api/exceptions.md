# Exceptions

All RLM exceptions inherit from `RLMError`.

## Exception Hierarchy

```
RLMError
├── SecurityViolationError  # gVisor missing, security bypass attempted
├── DataLeakageError        # Egress filter detected secret
├── SandboxError            # Docker execution failed
├── ContextError            # Context file issues
├── LLMError                # LLM API failures
├── BudgetExceededError     # Token budget exceeded
└── ConfigurationError      # Invalid configuration
```

## Reference

::: rlm.core.exceptions.RLMError
    handler: python
    options:
      show_root_full_path: false

::: rlm.core.exceptions.SecurityViolationError
    handler: python
    options:
      show_root_full_path: false

::: rlm.core.exceptions.DataLeakageError
    handler: python
    options:
      show_root_full_path: false

::: rlm.core.exceptions.SandboxError
    handler: python
    options:
      show_root_full_path: false

::: rlm.core.exceptions.ContextError
    handler: python
    options:
      show_root_full_path: false

## Handling Exceptions

```python
from rlm import Orchestrator
from rlm.core.exceptions import (
    SecurityViolationError,
    DataLeakageError,
    SandboxError,
    BudgetExceededError,
)

agent = Orchestrator()

try:
    result = await agent.arun("Do something")
except SecurityViolationError as e:
    # gVisor not available, unsafe runtime not allowed
    print(f"Security issue: {e}")
except DataLeakageError as e:
    # Egress filter detected potential secret
    print(f"Data leak prevented: {e}")
    print(f"Leak type: {e.leak_type}")
except SandboxError as e:
    # Docker execution failed
    print(f"Sandbox error: {e}")
    print(f"Exit code: {e.exit_code}")
except BudgetExceededError as e:
    # Token budget exceeded
    print(f"Budget exceeded: {e}")
```
