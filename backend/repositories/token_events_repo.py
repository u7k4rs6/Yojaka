from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import Currency, TokenEvent
from storage.models import TokenEventRow


class TokenEventsRepo:
    """
    Append-only ledger — rows are NEVER updated or deleted after insert.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def insert(self, event: TokenEvent) -> None:
        row = TokenEventRow(
            id=str(event.id),
            session_id=str(event.session_id),
            debate_id=str(event.debate_id) if event.debate_id else None,
            message_id=str(event.message_id),
            agent_role=event.agent_role,
            model=event.model,
            provider=event.provider,
            tokens_in=event.tokens_in,
            tokens_out=event.tokens_out,
            cost_usd=float(event.cost_usd),
            currency=event.currency.value if isinstance(event.currency, Currency) else event.currency,
            converted_cost=float(event.converted_cost),
            timestamp=event.timestamp,
        )
        self.db.add(row)
        await self.db.flush()

    async def sum_for_session(
        self, session_id: str | UUID
    ) -> tuple[int, int, Decimal]:
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(TokenEventRow.tokens_in), 0),
                func.coalesce(func.sum(TokenEventRow.tokens_out), 0),
                func.coalesce(func.sum(TokenEventRow.cost_usd), 0.0),
            ).where(TokenEventRow.session_id == str(session_id))
        )
        row = result.one()
        tokens_in = int(row[0])
        tokens_out = int(row[1])
        cost_usd = Decimal(str(row[2]))
        return tokens_in, tokens_out, cost_usd

    async def sum_for_debate(
        self, debate_id: str | UUID
    ) -> tuple[int, int, Decimal]:
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(TokenEventRow.tokens_in), 0),
                func.coalesce(func.sum(TokenEventRow.tokens_out), 0),
                func.coalesce(func.sum(TokenEventRow.cost_usd), 0.0),
            ).where(TokenEventRow.debate_id == str(debate_id))
        )
        row = result.one()
        tokens_in = int(row[0])
        tokens_out = int(row[1])
        cost_usd = Decimal(str(row[2]))
        return tokens_in, tokens_out, cost_usd
