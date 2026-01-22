"""
Base LLM Client Interface.

v2.1: Added async methods (acomplete, astream) for non-blocking I/O.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Iterator, Literal, Optional


class Role(str, Enum):
    """Message role in the conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """A message in the conversation history."""

    role: Role | Literal["system", "user", "assistant"]
    content: str
    name: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary format for API calls."""
        d = {"role": str(self.role.value if isinstance(self.role, Role) else self.role), "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


@dataclass
class TokenUsage:
    """Token usage information from an API response."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """Response from an LLM API call."""

    content: str
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    finish_reason: Optional[str] = None
    raw_response: Optional[dict] = None


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM provider clients.

    v2.1: All providers must implement both sync and async methods:
    - complete() / acomplete() for full responses
    - stream() / astream() for streaming responses
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        """
        Initialize the LLM client.

        Args:
            api_key: API key for the provider
            model: Model name to use
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'anthropic')."""
        pass

    # ==================== Sync Methods ====================

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion from the model (synchronous).

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse containing the generated content
        """
        pass

    @abstractmethod
    def stream(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Iterator[str]:
        """
        Stream a completion from the model (synchronous).

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific arguments

        Yields:
            Chunks of the generated content
        """
        pass

    # ==================== Async Methods (v2.1) ====================

    @abstractmethod
    async def acomplete(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion from the model (asynchronous).

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse containing the generated content
        """
        pass

    @abstractmethod
    async def astream(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream a completion from the model (asynchronous).

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific arguments

        Yields:
            Chunks of the generated content
        """
        pass
        # Required for abstract async generator
        yield  # type: ignore

    # ==================== Utilities ====================

    def validate_api_key(self) -> bool:
        """
        Validate that the API key is working.

        Returns:
            True if the API key is valid
        """
        try:
            # Try a minimal request
            self.complete([Message(role="user", content="test")])
            return True
        except Exception:
            return False

