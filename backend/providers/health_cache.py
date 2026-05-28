from __future__ import annotations

import time
from typing import Optional


class HealthCache:
    """In-memory TTL cache for provider health status."""

    HEALTHY_TTL = 15 * 60       # 15 minutes
    SOFT_FAIL_TTL = 2 * 60      # 2 minutes
    HARD_FAIL_TTL = 6 * 60 * 60 # 6 hours

    def __init__(self) -> None:
        # Maps provider name → (healthy: bool, expires_at: float)
        self._store: dict[str, tuple[bool, float]] = {}

    def get(self, provider: str) -> Optional[bool]:
        """Return the cached health status, or None if unknown/expired."""
        entry = self._store.get(provider)
        if entry is None:
            return None
        healthy, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[provider]
            return None
        return healthy

    def set(self, provider: str, healthy: bool, ttl: int) -> None:
        """Store a health result that expires after *ttl* seconds."""
        self._store[provider] = (healthy, time.monotonic() + ttl)
