from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import CouncilSettings, SessionSettings
from repositories.sessions_repo import SessionsRepo
from repositories.agent_experience_repo import AgentExperienceRepo
from storage.database import get_db

router = APIRouter()


def _db(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    return db


# ── Session settings ──────────────────────────────────────────────────────────

@router.get("/api/sessions/{session_id}/settings")
async def get_session_settings(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = SessionsRepo(db)
    session = await repo.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.settings.model_dump()


@router.patch("/api/sessions/{session_id}/settings")
async def update_session_settings(
    session_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    repo = SessionsRepo(db)
    session = await repo.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    merged = session.settings.model_dump()
    merged.update(body)
    new_settings = SessionSettings(**merged)
    updated = await repo.update_settings(session_id, new_settings)
    return updated.settings.model_dump()


# ── Council settings (singleton) ─────────────────────────────────────────────

_council_settings = CouncilSettings()   # in-memory singleton for dev


@router.get("/api/council-settings")
async def get_council_settings():
    return _council_settings.model_dump()


@router.patch("/api/council-settings")
async def update_council_settings(body: dict):
    global _council_settings
    merged = _council_settings.model_dump()
    merged.update(body)
    _council_settings = CouncilSettings(**merged)
    return _council_settings.model_dump()


@router.post("/api/council-settings/reset-agent-experience", status_code=204)
async def reset_agent_experience(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    confirmation = body.get("confirmation") or body.get("confirm", "")
    if confirmation != "RESET COUNCIL IDENTITIES":
        raise HTTPException(status_code=400, detail="Invalid confirmation phrase")
    repo = AgentExperienceRepo(db)
    await repo.reset_all()
