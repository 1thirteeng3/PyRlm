"""
Google Generative AI Client.

Provides integration with Google's Gemini models.
"""

import logging
from typing import Iterator, Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from rlm.core.exceptions import LLMError
from rlm.llm.base import BaseLLMClient, LLMResponse, Message, TokenUsage

logger = logging.getLogger(__name__)


class GoogleClient(BaseLLMClient):
    """
    Google Generative AI client for Gemini models.

    Supports both regular and streaming completions.

    Example:
        >>> client = GoogleClient(api_key="...", model="gemini-1.5-pro")
        >>> response = client.complete([Message(role="user", content="Hello!")])
        >>> print(response.content)
    """

    DEFAULT_MODEL = "gemini-1.5-pro"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        """
        Initialize the Google client.

        Args:
            api_key: Google API key
            model: Model name (default: gemini-1.5-pro)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        super().__init__(api_key, model, temperature, max_tokens)

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)
        self._generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    @property
    def provider_name(self) -> str:
        return "google"

    def _convert_messages(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
    ) -> tuple[Optional[str], list[dict]]:
        """
        Convert messages to Google's format.

        Google uses 'user' and 'model' roles.
        """
        system = system_prompt
        converted = []

        for msg in messages:
            role = msg.role.value if hasattr(msg.role, "value") else msg.role

            if role == "system":
                system = msg.content
                continue

            # Map assistant to model
            google_role = "model" if role == "assistant" else "user"

            converted.append({
                "role": google_role,
                "parts": [msg.content],
            })

        return system, converted

    def complete(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a completion using Google's API.

        Args:
            messages: Conversation history
            system_prompt: Optional system prompt
            **kwargs: Additional arguments

        Returns:
            LLMResponse with the generated content
        """
        system, converted_messages = self._convert_messages(messages, system_prompt)

        try:
            # Rebuild model with system instruction if provided
            if system:
                model = genai.GenerativeModel(
                    self.model,
                    system_instruction=system,
                )
            else:
                model = self._model

            response = model.generate_content(
                converted_messages,
                generation_config=self._generation_config,
                **kwargs,
            )

            # Extract usage information
            usage = TokenUsage()
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = TokenUsage(
                    prompt_tokens=getattr(response.usage_metadata, "prompt_token_count", 0),
                    completion_tokens=getattr(response.usage_metadata, "candidates_token_count", 0),
                    total_tokens=getattr(response.usage_metadata, "total_token_count", 0),
                )

            return LLMResponse(
                content=response.text if response.text else "",
                model=self.model,
                usage=usage,
                finish_reason=str(response.candidates[0].finish_reason) if response.candidates else None,
                raw_response=None,  # Google's response doesn't have a simple dict export
            )

        except Exception as e:
            logger.error(f"Google API error: {e}")
            raise LLMError(
                message=f"Google API request failed: {e}",
                provider="google",
            ) from e

    def stream(
        self,
        messages: list[Message],
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Iterator[str]:
        """
        Stream a completion from Google.

        Args:
            messages: Conversation history
            system_prompt: Optional system prompt
            **kwargs: Additional arguments

        Yields:
            Chunks of the generated content
        """
        system, converted_messages = self._convert_messages(messages, system_prompt)

        try:
            if system:
                model = genai.GenerativeModel(
                    self.model,
                    system_instruction=system,
                )
            else:
                model = self._model

            response = model.generate_content(
                converted_messages,
                generation_config=self._generation_config,
                stream=True,
                **kwargs,
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Google streaming error: {e}")
            raise LLMError(
                message=f"Google streaming failed: {e}",
                provider="google",
            ) from e
