from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import Session, SessionMode, SessionSettings
from repositories.sessions_repo import SessionsRepo
from storage.database import get_db

router = APIRouter(prefix="/api/sessions")


def _repo(db: AsyncSession = Depends(get_db)) -> SessionsRepo:
    return SessionsRepo(db)


class CreateSessionRequest(BaseModel):
    name:     str = "New Session"
    mode:     SessionMode = SessionMode.AI_VS_AI
    settings: SessionSettings = SessionSettings()


class RenameRequest(BaseModel):
    name: str


@router.get("", response_model=list[Session])
async def list_sessions(
    x_client_id: str = Header(default=""),
    repo: SessionsRepo = Depends(_repo),
):
    return await repo.list_all(client_id=x_client_id)


@router.post("", response_model=Session, status_code=201)
async def create_session(
    body: CreateSessionRequest,
    x_client_id: str = Header(default=""),
    repo: SessionsRepo = Depends(_repo),
):
    return await repo.create(body.name, body.mode, body.settings, client_id=x_client_id)


@router.delete("", status_code=204)
async def delete_all_sessions(
    x_client_id: str = Header(default=""),
    repo: SessionsRepo = Depends(_repo),
):
    await repo.delete_all(client_id=x_client_id)


@router.patch("/{session_id}", response_model=Session)
async def rename_session(
    session_id: UUID,
    body: RenameRequest,
    repo: SessionsRepo = Depends(_repo),
):
    return await repo.rename(session_id, body.name)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: UUID,
    repo: SessionsRepo = Depends(_repo),
):
    await repo.delete(session_id)


@router.post("/{session_id}/clear-history", status_code=204)
async def clear_history(
    session_id: UUID,
    repo: SessionsRepo = Depends(_repo),
):
    await repo.clear_history(session_id)


@router.post("/{session_id}/clear-memory", status_code=204)
async def clear_memory(
    session_id: UUID,
    repo: SessionsRepo = Depends(_repo),
):
    await repo.clear_memory(session_id)
