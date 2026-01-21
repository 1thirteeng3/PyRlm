"""
Custom exceptions for RLM.

This module defines the exception hierarchy for all RLM-related errors.
"""

from typing import Optional


class RLMError(Exception):
    """Base exception for all RLM errors."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class SecurityViolationError(RLMError):
    """
    Raised when a security boundary is violated.

    This includes attempts to escape the sandbox, access restricted
    resources, or perform unauthorized operations.
    """

    def __init__(
        self,
        message: str = "Security violation detected",
        violation_type: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message, details)
        self.violation_type = violation_type


class DataLeakageError(SecurityViolationError):
    """
    Raised when potential data leakage is detected.

    This is triggered by the egress filter when:
    - High entropy data (potential secrets) is detected in output
    - Output closely matches the input context (echo attack)
    """

    def __init__(
        self,
        message: str = "Potential data leakage detected",
        leak_type: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message, violation_type="data_leakage", details=details)
        self.leak_type = leak_type


class BudgetExceededError(RLMError):
    """
    Raised when the cost limit is exceeded.

    This prevents runaway API costs by stopping execution when
    the configured spending limit is reached.
    """

    def __init__(
        self,
        message: str = "Budget limit exceeded",
        spent: float = 0.0,
        limit: float = 0.0,
        details: Optional[dict] = None,
    ) -> None:
        details = details or {}
        details.update({"spent_usd": spent, "limit_usd": limit})
        super().__init__(message, details)
        self.spent = spent
        self.limit = limit


class SandboxError(RLMError):
    """
    Raised when sandbox execution fails.

    This includes container startup failures, timeout issues,
    and resource limit violations (OOM, CPU quota, etc.).
    """

    def __init__(
        self,
        message: str = "Sandbox execution failed",
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        details = details or {}
        if exit_code is not None:
            details["exit_code"] = exit_code
        if stderr:
            details["stderr"] = stderr[:500]  # Truncate for safety
        super().__init__(message, details)
        self.exit_code = exit_code
        self.stderr = stderr

    @property
    def is_oom_killed(self) -> bool:
        """Check if the container was killed due to OOM."""
        return self.exit_code == 137

    @property
    def is_timeout(self) -> bool:
        """Check if the execution timed out."""
        return self.exit_code == 124


class ContextError(RLMError):
    """
    Raised when there's an issue with context handling.

    This includes file not found, encoding issues, or memory
    mapping failures.
    """

    def __init__(
        self,
        message: str = "Context handling error",
        path: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        details = details or {}
        if path:
            details["path"] = path
        super().__init__(message, details)
        self.path = path


class ConfigurationError(RLMError):
    """
    Raised when there's a configuration issue.

    This includes missing API keys, invalid settings, or
    unavailable Docker runtime.
    """

    def __init__(
        self,
        message: str = "Configuration error",
        setting_name: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        details = details or {}
        if setting_name:
            details["setting"] = setting_name
        super().__init__(message, details)
        self.setting_name = setting_name


class LLMError(RLMError):
    """
    Raised when there's an error communicating with the LLM.

    This includes API errors, rate limiting, and model-specific issues.
    """

    def __init__(
        self,
        message: str = "LLM error",
        provider: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[dict] = None,
    ) -> None:
        details = details or {}
        if provider:
            details["provider"] = provider
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details)
        self.provider = provider
        self.status_code = status_code
