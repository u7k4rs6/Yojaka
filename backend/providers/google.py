from __future__ import annotations

import logging
from typing import AsyncIterator

from config import settings
from providers.base import AuthError, ProviderClient, ProviderError, RateLimitError

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai  # type: ignore
    import google.api_core.exceptions as google_exceptions  # type: ignore
    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False


def _messages_to_gemini(messages: list[dict]) -> tuple[list, str | None]:
    """Convert OpenAI-format messages to Gemini contents + system instruction.

    Returns (contents, system_instruction_text | None).
    """
    system_parts: list[str] = []
    contents: list[dict] = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_parts.append(content)
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": content}]})
        else:
            contents.append({"role": "user", "parts": [{"text": content}]})

    system_text = "\n\n".join(system_parts) if system_parts else None

    # Gemini requires the first turn to be a user turn.
    if not contents:
        contents = [{"role": "user", "parts": [{"text": "Hello"}]}]

    return contents, system_text


def _translate_error(exc: Exception) -> ProviderError:
    """Map a google-api exception to our error hierarchy."""
    if _GOOGLE_AVAILABLE:
        if isinstance(exc, google_exceptions.ResourceExhausted):
            return RateLimitError(str(exc))
        if isinstance(exc, (google_exceptions.Unauthenticated, google_exceptions.PermissionDenied)):
            return AuthError(str(exc))
    return ProviderError(str(exc))


class GoogleProvider(ProviderClient):
    """Google Gemini provider."""

    name = "google"
    available = _GOOGLE_AVAILABLE and bool(settings.google_api_key)

    def __init__(self) -> None:
        if self.available:
            genai.configure(api_key=settings.google_api_key)

    async def stream_chat(
        self,
        messages: list[dict],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        if not self.available:
            raise ProviderError("Google provider not available (missing API key or library)")

        contents, system_text = _messages_to_gemini(messages)
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        kwargs: dict = {}
        if system_text:
            kwargs["system_instruction"] = system_text

        try:
            gm = genai.GenerativeModel(model, **kwargs)
            response = await gm.generate_content_async(
                contents,
                stream=True,
                generation_config=generation_config,
            )
            async for chunk in response:
                text = chunk.text
                if text:
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
            raise ProviderError("Google provider not available")

        try:
            gm = genai.GenerativeModel(model)
            response = await gm.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens),
            )
            return response.text or ""
        except Exception as exc:
            raise _translate_error(exc) from exc

    async def probe(self) -> bool:
        try:
            result = await self.complete("hi", model="gemini-2.0-flash", max_tokens=4)
            return bool(result)
        except ProviderError:
            return False
        except Exception:
            return False
