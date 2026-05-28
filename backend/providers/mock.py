from __future__ import annotations

from typing import AsyncIterator

from providers.base import ProviderClient


class MockProvider(ProviderClient):
    """Deterministic mock provider for testing and development."""

    name = "mock"
    available = True

    _CHUNKS = ["This ", "is a ", "mock ", "debate ", "response."]

    async def stream_chat(
        self,
        messages: list[dict],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        for chunk in self._CHUNKS:
            yield chunk

    async def complete(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int = 100,
    ) -> str:
        return "YES"

    async def probe(self) -> bool:
        return True
