"""
OpenAI LLM Client.

Provides integration with OpenAI's GPT models (GPT-4, GPT-4o, etc.).
"""

import logging
from typing import Iterator, Optional

from openai import OpenAI

from rlm.core.exceptions import LLMError
from rlm.llm.base import BaseLLMClient, LLMResponse, Message, TokenUsage

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """
    OpenAI API client for GPT models.

    Supports both regular and streaming completions.

    Example:
        >>> client = OpenAIClient(api_key="sk-...", model="gpt-4o")
        >>> response = client.complete([Message(role="user", content="Hello!")])
        >>> print(response.content)
    """

    DEFAULT_MODEL = "gpt-4o"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        base_url: Optional[str] = None,
    ) -> None:
        """
        Initialize the OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            base_url: Optional custom base URL (for Azure or proxies)
        """
        super().__init__(api_key, model, temperature, max_tokens)
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    @property
    def provider_name(self) -> str:
        return "openai"

    def complete(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion using OpenAI's API.

        Args:
            messages: Conversation history
            system_prompt: Optional system prompt
            **kwargs: Additional arguments (passed to API)

        Returns:
            LLMResponse with the generated content
        """
        all_messages = []

        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})

        all_messages.extend([m.to_dict() for m in messages])

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=all_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs,
            )

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                usage=TokenUsage(
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                ),
                finish_reason=choice.finish_reason,
                raw_response=response.model_dump() if hasattr(response, "model_dump") else None,
            )

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMError(
                message=f"OpenAI API request failed: {e}",
                provider="openai",
            ) from e

    def stream(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Iterator[str]:
        """
        Stream a completion from OpenAI.

        Args:
            messages: Conversation history
            system_prompt: Optional system prompt
            **kwargs: Additional arguments

        Yields:
            Chunks of the generated content
        """
        all_messages = []

        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})

        all_messages.extend([m.to_dict() for m in messages])

        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=all_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                **kwargs,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise LLMError(
                message=f"OpenAI streaming failed: {e}",
                provider="openai",
            ) from e
