from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import TYPE_CHECKING, Literal
from uuid import UUID

if TYPE_CHECKING:
    from repositories.token_events_repo import TokenEventsRepo


class BudgetExhausted(Exception):
    pass


class SessionBudget:
    def __init__(self, session_id: UUID, cap: int) -> None:
        self.session_id = session_id
        self.cap        = cap
        self.consumed   = 0
        self.reserved   = 0
        self._lock      = asyncio.Lock()

    @property
    def status(self) -> Literal["healthy", "warning", "exhausted"]:
        used = self.consumed + self.reserved
        if used >= self.cap:
            return "exhausted"
        if used >= self.cap * 0.9:
            return "warning"
        return "healthy"

    async def reserve(self, amount: int) -> bool:
        """
        Reserve `amount` tokens from the outstanding reservation queue.
        Fails only when the reservation queue alone would exceed cap.
        (Consumed tokens represent already-settled usage and don't block new reservations.)
        """
        async with self._lock:
            if self.reserved + amount > self.cap:
                return False
            self.reserved += amount
            return True

    async def charge(self, actual_out: int, reserved: int) -> None:
        """Reconcile: consume actual_out, release `reserved` from the reservation."""
        async with self._lock:
            self.reserved  = max(0, self.reserved - reserved)
            self.consumed += actual_out

    async def hydrate_from_ledger(self, repo: "TokenEventsRepo") -> None:
        """Restore consumed count from the token_events append-only ledger."""
        _, tokens_out, _ = await repo.sum_for_session(self.session_id)
        async with self._lock:
            self.consumed = tokens_out
