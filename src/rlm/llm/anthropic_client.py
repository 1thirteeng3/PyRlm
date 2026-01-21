"""
Anthropic LLM Client.

Provides integration with Anthropic's Claude models.
"""

import logging
from typing import Iterator, Optional

import anthropic

from rlm.core.exceptions import LLMError
from rlm.llm.base import BaseLLMClient, LLMResponse, Message, TokenUsage

logger = logging.getLogger(__name__)


class AnthropicClient(BaseLLMClient):
    """
    Anthropic API client for Claude models.

    Supports both regular and streaming completions.

    Example:
        >>> client = AnthropicClient(api_key="sk-...", model="claude-3-sonnet-20240229")
        >>> response = client.complete([Message(role="user", content="Hello!")])
        >>> print(response.content)
    """

    DEFAULT_MODEL = "claude-3-sonnet-20240229"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key
            model: Model name (default: claude-3-sonnet)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        super().__init__(api_key, model, temperature, max_tokens)
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _convert_messages(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
    ) -> tuple[Optional[str], list[dict]]:
        """
        Convert messages to Anthropic's format.

        Anthropic uses a separate system parameter instead of a message.

        Returns:
            Tuple of (system_prompt, messages)
        """
        system = system_prompt
        converted = []

        for msg in messages:
            role = msg.role.value if hasattr(msg.role, "value") else msg.role

            # Extract system messages
            if role == "system":
                system = msg.content
                continue

            converted.append({
                "role": role,
                "content": msg.content,
            })

        return system, converted

    def complete(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion using Anthropic's API.

        Args:
            messages: Conversation history
            system_prompt: Optional system prompt
            **kwargs: Additional arguments

        Returns:
            LLMResponse with the generated content
        """
        system, converted_messages = self._convert_messages(messages, system_prompt)

        try:
            create_kwargs = {
                "model": self.model,
                "messages": converted_messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                **kwargs,
            }

            if system:
                create_kwargs["system"] = system

            response = self._client.messages.create(**create_kwargs)

            # Extract content from response
            content = ""
            if response.content:
                content = response.content[0].text

            return LLMResponse(
                content=content,
                model=response.model,
                usage=TokenUsage(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                ),
                finish_reason=response.stop_reason,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise LLMError(
                message=f"Anthropic API request failed: {e}",
                provider="anthropic",
            ) from e

    def stream(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Iterator[str]:
        """
        Stream a completion from Anthropic.

        Args:
            messages: Conversation history
            system_prompt: Optional system prompt
            **kwargs: Additional arguments

        Yields:
            Chunks of the generated content
        """
        system, converted_messages = self._convert_messages(messages, system_prompt)

        try:
            create_kwargs = {
                "model": self.model,
                "messages": converted_messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                **kwargs,
            }

            if system:
                create_kwargs["system"] = system

            with self._client.messages.stream(**create_kwargs) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            raise LLMError(
                message=f"Anthropic streaming failed: {e}",
                provider="anthropic",
            ) from e
