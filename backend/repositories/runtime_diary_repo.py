from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from storage.models import RuntimeDiaryRow


class RuntimeDiaryRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        source: str,
        event: str,
        detail: str,
        session_id: Optional[str] = None,
    ) -> None:
        row = RuntimeDiaryRow(
            source=source,
            event=event,
            detail=detail,
            session_id=str(session_id) if session_id else None,
            # timestamp uses server_default=func.now() from the ORM model
        )
        self.db.add(row)
        # flush is deferred to the outer commit to avoid conflicts with concurrent inserts
        try:
            await self.db.flush()
        except Exception:
            pass  # will be committed by outer context

    async def recent(self, limit: int = 100) -> list[dict]:
        result = await self.db.execute(
            select(RuntimeDiaryRow)
            .order_by(RuntimeDiaryRow.timestamp.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        # Return in chronological order (oldest first within the window)
        return [
            {
                "id": r.id,
                "source": r.source,
                "event": r.event,
                "detail": r.detail,
                "session_id": r.session_id,
                "timestamp": r.timestamp,
            }
            for r in reversed(rows)
        ]
