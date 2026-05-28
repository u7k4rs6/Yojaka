from __future__ import annotations

import logging
from typing import AsyncIterator

from providers.base import AuthError, ProviderClient, ProviderError, RateLimitError
from providers.health_cache import HealthCache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model → provider mapping
# ---------------------------------------------------------------------------

MODEL_TO_PROVIDER: dict[str, str] = {
    # Google
    "gemini-3.1-pro":        "google",
    "gemini-3-flash":        "google",
    "gemini-2.5-flash-lite": "google",
    "gemini-2.0-flash":      "google",
    # Groq
    "llama-3.1-8b-instant":    "groq",
    "llama-3.3-70b-versatile": "groq",
    # OpenRouter
    "openrouter-auto":       "openrouter",
    "llama-3.3-70b-or":      "openrouter",
    "claude-3.5-sonnet-or":  "openrouter",
    "deepseek-r1-free":      "openrouter",
    "qwq-32b-free":          "openrouter",
    "llama-3.1-8b-free":     "openrouter",
    "gemma-3-27b-free":      "openrouter",
    "qwen3-14b-free":        "openrouter",
    # Moonshot
    "kimi-latest":              "moonshot",
    "kimi-k2-thinking":         "moonshot",
    "kimi-k2-turbo-preview":    "moonshot",
    "kimi-k2.5-vision":         "moonshot",
    "moonshot-v1-128k":         "moonshot",
    # OpenAI
    "gpt-4o":      "openai",
    "gpt-4o-mini": "openai",
    # Anthropic
    "claude-opus-4-6":    "anthropic",
    "claude-sonnet-4-6":  "anthropic",
    "claude-haiku-4-5":   "anthropic",
    "claude-3.5-sonnet":  "anthropic",
    # Mock
    "mock-debate-model": "mock",
}

# Default model per provider (cheapest/fastest)
_PROVIDER_DEFAULT_MODEL: dict[str, str] = {
    "google":      "gemini-2.0-flash",
    "groq":        "llama-3.1-8b-instant",
    "openrouter":  "openrouter-auto",
    "moonshot":    "moonshot-v1-128k",
    "openai":      "gpt-4o-mini",
    "anthropic":   "claude-haiku-4-5",
    "mock":        "mock-debate-model",
}


class ProviderRouter:
    """Routes model calls to the correct provider, with health-aware fallback."""

    def __init__(
        self,
        clients: dict[str, ProviderClient],
        health_cache: HealthCache,
    ) -> None:
        self._clients = clients
        self._health = health_cache

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _available_providers_in_order(self) -> list[str]:
        """Return provider names whose client is available and not hard-failed.

        The order is deterministic: google, groq, openrouter, moonshot, openai,
        anthropic, mock — so that slot-based selection is stable.
        """
        preferred_order = [
            "google", "groq", "openrouter", "moonshot", "openai", "anthropic", "mock"
        ]
        result: list[str] = []
        for name in preferred_order:
            client = self._clients.get(name)
            if client is None or not client.available:
                continue
            cached = self._health.get(name)
            if cached is False:
                continue  # currently marked unhealthy
            result.append(name)
        return result

    # ------------------------------------------------------------------
    # resolve_model
    # ------------------------------------------------------------------

    def resolve_model(self, assignment, council, user_primary: str) -> str:
        """Decide which model to use for a given AgentAssignment.

        Priority:
        1. Per-agent model override in assignment.settings.model
        2. assignment.model field
        3. Slot 0 (judge / council / practice roles) → user_primary
        4. Slot 1 (pro team) → second available provider's default model
        5. Slot 2 (con team) → third available provider's default model
        """
        # 1. Per-agent settings override
        if assignment.settings and assignment.settings.model:
            return assignment.settings.model

        # 2. Top-level model field on the assignment itself
        if assignment.model:
            return assignment.model

        slot: int = assignment.slot
        available = self._available_providers_in_order()

        if slot == 0:
            return user_primary

        # Determine the provider that user_primary belongs to so we can diversify
        primary_provider = MODEL_TO_PROVIDER.get(user_primary, "")
        other_providers = [p for p in available if p != primary_provider]

        if slot == 1:
            if other_providers:
                return _PROVIDER_DEFAULT_MODEL.get(other_providers[0], user_primary)
            return user_primary

        # slot == 2
        if len(other_providers) >= 2:
            return _PROVIDER_DEFAULT_MODEL.get(other_providers[1], user_primary)
        if other_providers:
            return _PROVIDER_DEFAULT_MODEL.get(other_providers[0], user_primary)
        return user_primary

    # ------------------------------------------------------------------
    # call (async generator)
    # ------------------------------------------------------------------

    async def call(
        self,
        *,
        model: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Yield text chunks from the provider responsible for *model*.

        On RateLimitError the provider is soft-failed and a mock fallback is
        attempted.  On AuthError the provider is hard-failed and the error is
        re-raised.
        """
        provider_name = MODEL_TO_PROVIDER.get(model)
        if provider_name is None:
            raise ProviderError(f"Unknown model '{model}' — not in MODEL_TO_PROVIDER")

        client = self._clients.get(provider_name)
        if client is None or not client.available:
            raise ProviderError(f"Provider '{provider_name}' not configured or unavailable")

        try:
            async for chunk in client.stream_chat(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield chunk

        except RateLimitError as exc:
            logger.warning(
                "Rate-limit on provider '%s': %s — soft-failing for %ds",
                provider_name,
                exc,
                HealthCache.SOFT_FAIL_TTL,
            )
            self._health.set(provider_name, False, HealthCache.SOFT_FAIL_TTL)
            # Fall back to mock if available
            async for chunk in self._mock_fallback(messages, max_tokens):
                yield chunk

        except AuthError:
            logger.error(
                "Auth error on provider '%s' — hard-failing for %ds",
                provider_name,
                HealthCache.HARD_FAIL_TTL,
            )
            self._health.set(provider_name, False, HealthCache.HARD_FAIL_TTL)
            raise

    async def _mock_fallback(
        self,
        messages: list[dict],
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Stream from the mock provider as a last-resort fallback."""
        mock = self._clients.get("mock")
        if mock and mock.available:
            async for chunk in mock.stream_chat(
                messages,
                model="mock-debate-model",
                temperature=0.5,
                max_tokens=max_tokens,
            ):
                yield chunk
        else:
            yield "[Provider temporarily unavailable. Please retry.]"
