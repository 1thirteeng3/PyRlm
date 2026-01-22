# Exceptions API

All RLM exceptions inherit from `RLMError`.

## Base Exception

::: rlm.core.exceptions.RLMError
    options:
      show_source: true

## Security Exceptions

::: rlm.core.exceptions.SecurityViolationError
    options:
      show_source: true

::: rlm.core.exceptions.DataLeakageError
    options:
      show_source: true

## Execution Exceptions

::: rlm.core.exceptions.SandboxError
    options:
      show_source: true

::: rlm.core.exceptions.BudgetExceededError
    options:
      show_source: true

## Configuration Exceptions

::: rlm.core.exceptions.ConfigurationError
    options:
      show_source: true

::: rlm.core.exceptions.ContextError
    options:
      show_source: true

## LLM Exceptions

::: rlm.core.exceptions.LLMError
    options:
      show_source: true
