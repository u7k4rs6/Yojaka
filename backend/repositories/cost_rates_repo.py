from __future__ import annotations

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import CostRate
from storage.models import CostRateRow


def _row_to_cost_rate(row: CostRateRow) -> CostRate:
    return CostRate(
        model=row.model,
        provider=row.provider or "",
        input_rate_per_1m=row.input_rate_per_1m or 0.0,
        output_rate_per_1m=row.output_rate_per_1m or 0.0,
        pricing_available=bool(row.pricing_available),
        source=row.source,
        fetched_at=row.fetched_at,
    )


class CostRatesRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, model: str) -> Optional[CostRate]:
        result = await self.db.execute(
            select(CostRateRow).where(CostRateRow.model == model)
        )
        row = result.scalar_one_or_none()
        return _row_to_cost_rate(row) if row else None

    async def upsert(self, rate: CostRate) -> None:
        result = await self.db.execute(
            select(CostRateRow).where(CostRateRow.model == rate.model)
        )
        existing = result.scalar_one_or_none()

        if existing:
            await self.db.execute(
                update(CostRateRow)
                .where(CostRateRow.model == rate.model)
                .values(
                    provider=rate.provider,
                    input_rate_per_1m=rate.input_rate_per_1m,
                    output_rate_per_1m=rate.output_rate_per_1m,
                    pricing_available=rate.pricing_available,
                    source=rate.source,
                    fetched_at=rate.fetched_at,
                )
            )
        else:
            row = CostRateRow(
                model=rate.model,
                provider=rate.provider,
                input_rate_per_1m=rate.input_rate_per_1m,
                output_rate_per_1m=rate.output_rate_per_1m,
                pricing_available=rate.pricing_available,
                source=rate.source,
                fetched_at=rate.fetched_at,
            )
            self.db.add(row)

        await self.db.flush()

    async def list_all(self) -> list[CostRate]:
        result = await self.db.execute(
            select(CostRateRow).order_by(CostRateRow.model.asc())
        )
        rows = result.scalars().all()
        return [_row_to_cost_rate(r) for r in rows]
