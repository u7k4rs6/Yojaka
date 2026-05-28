from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.messages_repo import MessagesRepo
from repositories.debates_repo import DebatesRepo
from storage.database import get_db

router = APIRouter()


@router.get("/api/sessions/{session_id}/messages")
async def get_messages(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = MessagesRepo(db)
    msgs = await repo.list_for_session(session_id)
    return [m.model_dump() for m in msgs]


@router.get("/api/sessions/{session_id}/debates")
async def get_debates(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = DebatesRepo(db)
    debates = await repo.list_for_session(session_id)
    return [d.model_dump() for d in debates]


@router.patch("/api/sessions/{session_id}/debates/{debate_id}")
async def rename_debate(
    session_id: UUID,
    debate_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    repo = DebatesRepo(db)
    debate = await repo.get(debate_id)
    if not debate or debate.session_id != session_id:
        raise HTTPException(status_code=404, detail="Debate not found")
    topic = body.get("topic")
    if topic:
        debate = await repo.rename(debate_id, topic)
    return debate.model_dump()


@router.delete("/api/sessions/{session_id}/debates/{debate_id}", status_code=204)
async def delete_debate(
    session_id: UUID,
    debate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = DebatesRepo(db)
    debate = await repo.get(debate_id)
    if not debate or debate.session_id != session_id:
        raise HTTPException(status_code=404, detail="Debate not found")
    await repo.hide(debate_id)


@router.get("/api/sessions/{session_id}/practice-state")
async def get_practice_state(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = DebatesRepo(db)
    debates = await repo.list_for_session(session_id)
    # Return the practice_state of the most recent debate with one
    for d in reversed(debates):
        if d.practice_state:
            return d.practice_state
    return {}
