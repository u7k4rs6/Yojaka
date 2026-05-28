from __future__ import annotations

import logging
from typing import AsyncIterator

from config import settings
from providers.base import AuthError, ProviderClient, ProviderError, RateLimitError

logger = logging.getLogger(__name__)

try:
    import openai as openai_lib  # type: ignore
    from openai import AsyncOpenAI  # type: ignore
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

_MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"


def _translate_error(exc: Exception) -> ProviderError:
    """Map an openai/moonshot exception to our error hierarchy."""
    if _OPENAI_AVAILABLE:
        if isinstance(exc, openai_lib.RateLimitError):
            return RateLimitError(str(exc))
        if isinstance(exc, openai_lib.AuthenticationError):
            return AuthError(str(exc))
    msg = str(exc)
    if "429" in msg:
        return RateLimitError(msg)
    if "401" in msg:
        return AuthError(msg)
    return ProviderError(msg)


class MoonshotProvider(ProviderClient):
    """Moonshot Kimi provider (OpenAI-compatible API)."""

    name = "moonshot"
    available = _OPENAI_AVAILABLE and bool(settings.moonshot_api_key)

    def __init__(self) -> None:
        if self.available:
            self._client = AsyncOpenAI(
                api_key=settings.moonshot_api_key,
                base_url=_MOONSHOT_BASE_URL,
            )
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
            raise ProviderError("Moonshot provider not available (missing API key or library)")

        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content or ""
                yield content
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
            raise ProviderError("Moonshot provider not available")

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                stream=False,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise _translate_error(exc) from exc

    async def probe(self) -> bool:
        try:
            result = await self.complete("hi", model="moonshot-v1-128k", max_tokens=4)
            return bool(result)
        except ProviderError:
            return False
        except Exception:
            return False
