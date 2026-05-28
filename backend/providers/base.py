from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator


class ProviderError(Exception):
    """Base class for all provider errors."""


class RateLimitError(ProviderError):
    """Raised when the provider returns a 429 rate-limit response."""


class AuthError(ProviderError):
    """Raised when the provider returns a 401/403 authentication error."""


class ProviderClient(ABC):
    name: str
    available: bool

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict],
        *,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> AsyncIterator[str]:
        """Yield text chunks. Raises ProviderError on failure."""
        ...

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        model: str,
        max_tokens: int = 100,
    ) -> str:
        """Return a single completion string."""
        ...

    @abstractmethod
    async def probe(self) -> bool:
        """Send a 4-token test. Returns True if healthy."""
        ...
