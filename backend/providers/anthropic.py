from __future__ import annotations

import logging
from typing import AsyncIterator

from config import settings
from providers.base import AuthError, ProviderClient, ProviderError, RateLimitError

logger = logging.getLogger(__name__)

try:
    import anthropic as anthropic_lib  # type: ignore
    from anthropic import AsyncAnthropic  # type: ignore
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


def _translate_error(exc: Exception) -> ProviderError:
    """Map an anthropic exception to our error hierarchy."""
    if _ANTHROPIC_AVAILABLE:
        if isinstance(exc, anthropic_lib.RateLimitError):
            return RateLimitError(str(exc))
        if isinstance(exc, anthropic_lib.AuthenticationError):
            return AuthError(str(exc))
    msg = str(exc)
    if "429" in msg:
        return RateLimitError(msg)
    if "401" in msg or "403" in msg:
        return AuthError(msg)
    return ProviderError(msg)


def _extract_system(messages: list[dict]) -> tuple[list[dict], str]:
    """Separate system message(s) from the message list.

    Returns (non_system_messages, system_text).
    """
    system_parts: list[str] = []
    rest: list[dict] = []
    for msg in messages:
        if msg.get("role") == "system":
            system_parts.append(msg.get("content", ""))
        else:
            rest.append(msg)
    return rest, "\n\n".join(system_parts)


class AnthropicProvider(ProviderClient):
    """Anthropic Claude provider."""

    name = "anthropic"
    available = _ANTHROPIC_AVAILABLE and bool(settings.anthropic_api_key)

    def __init__(self) -> None:
        if self.available:
            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        else:
            self._client = None  # type: ignore[assignment]

    async def stream_chat(
        self,
        messages: list[dict],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        if not self.available:
            raise ProviderError("Anthropic provider not available (missing API key or library)")

        non_system_messages, system_text = _extract_system(messages)

        kwargs: dict = {}
        if system_text:
            kwargs["system"] = system_text

        try:
            async with self._client.messages.stream(
                model=model,
                messages=non_system_messages,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as exc:
            raise _translate_error(exc) from exc

    async def complete(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int = 100,
    ) -> str:
        if not self.available:
            raise ProviderError("Anthropic provider not available")

        try:
            response = await self._client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return response.content[0].text
        except Exception as exc:
            raise _translate_error(exc) from exc

    async def probe(self) -> bool:
        try:
            result = await self.complete("hi", model="claude-haiku-4-5", max_tokens=4)
            return bool(result)
        except ProviderError:
            return False
        except Exception:
            return False
