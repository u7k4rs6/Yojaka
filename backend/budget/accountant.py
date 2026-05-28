from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from core.schemas import Currency, TokenEvent
from budget.cost_rates import LOCAL_FALLBACK_RATES
from budget.tokenizer import estimate_tokens, count_tokens
from repositories.cost_rates_repo import CostRatesRepo
from repositories.token_events_repo import TokenEventsRepo

# Exchange rates vs USD (approximate; production should refresh from a live feed)
_FX: dict[str, float] = {
    "USD": 1.0,
    "CNY": 7.25,
    "HKD": 7.82,
    "EUR": 0.92,
    "JPY": 149.0,
    "GBP": 0.79,
    "AUD": 1.53,
    "CAD": 1.36,
    "SGD": 1.34,
}


class TokenAccountant:
    def __init__(self, rates_repo: CostRatesRepo, events_repo: TokenEventsRepo) -> None:
        self._rates  = rates_repo
        self._events = events_repo

    def estimate_tokens(self, text: str) -> int:
        return estimate_tokens(text)

    def count_tokens(self, text: str) -> int:
        return count_tokens(text)

    async def compute_cost(self, tokens_in: int, tokens_out: int, model: str) -> Decimal:
        rate = None
        if self._rates is not None:
            rate = await self._rates.get(model)
        if rate is None:
            rate = LOCAL_FALLBACK_RATES.get(model)
        if rate is None:
            return Decimal("0")
        cost = Decimal(str(tokens_in))  / Decimal("1000000") * Decimal(str(rate.input_rate_per_1m)) \
             + Decimal(str(tokens_out)) / Decimal("1000000") * Decimal(str(rate.output_rate_per_1m))
        return cost

    async def convert_currency(self, usd: Decimal, currency: Currency) -> Decimal:
        fx = Decimal(str(_FX.get(currency.value, 1.0)))
        return usd * fx

    async def record(
        self,
        *,
        session_id: UUID,
        debate_id: Optional[UUID],
        message_id: UUID,
        agent_role: str,
        model: str,
        provider: str,
        tokens_in: int,
        tokens_out: int,
        currency: Currency = Currency.USD,
    ) -> TokenEvent:
        cost_usd       = await self.compute_cost(tokens_in, tokens_out, model)
        converted_cost = await self.convert_currency(cost_usd, currency)
        event = TokenEvent(
            id             = uuid4(),
            session_id     = session_id,
            debate_id      = debate_id,
            message_id     = message_id,
            agent_role     = agent_role,
            model          = model,
            provider       = provider,
            tokens_in      = tokens_in,
            tokens_out     = tokens_out,
            cost_usd       = cost_usd,
            currency       = currency,
            converted_cost = converted_cost,
            timestamp      = datetime.now(timezone.utc),
        )
        if self._events is not None:
            await self._events.insert(event)
        return event
