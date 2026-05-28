from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.runtime_diary_repo import RuntimeDiaryRepo
from storage.database import get_db

router = APIRouter(prefix="/api")


class DiaryEntry(BaseModel):
    source:     str
    event:      str
    detail:     str
    session_id: Optional[str] = None


@router.post("/runtime-diary", status_code=204)
async def log_diary(
    body: DiaryEntry,
    db: AsyncSession = Depends(get_db),
):
    repo = RuntimeDiaryRepo(db)
    sid = UUID(body.session_id) if body.session_id else None
    await repo.log(body.source, body.event, body.detail, session_id=sid)


@router.get("/runtime-diary/recent")
async def get_recent_diary(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    repo = RuntimeDiaryRepo(db)
    return await repo.recent(limit=limit)
