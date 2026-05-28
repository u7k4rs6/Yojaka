from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.debates_repo import DebatesRepo
from repositories.intelligence_repo import IntelligenceRepo
from storage.database import get_db

router = APIRouter()


@router.get("/api/sessions/{session_id}/analytics")
async def get_analytics(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = DebatesRepo(db)
    debates = await repo.list_for_session(session_id)
    # Return analytics from most recent completed debate
    for d in reversed(debates):
        if d.analytics:
            return d.analytics
    return {}


@router.get("/api/sessions/{session_id}/intelligence")
async def get_intelligence(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = IntelligenceRepo(db)
    records = await repo.list_for_session(session_id)
    return [r.model_dump() for r in records]


@router.post("/api/sessions/{session_id}/debates/{debate_id}/feedback", status_code=204)
async def submit_feedback(
    session_id: UUID,
    debate_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    # Feedback stored as an intelligence record (post_debate_feedback)
    from datetime import datetime, timezone
    from uuid import uuid4
    from core.schemas import IntelligenceRecord, IntelligenceType, Team
    repo = IntelligenceRepo(db)
    answers = body.get("answers", [])
    content = " | ".join(str(a) for a in answers)
    record = IntelligenceRecord(
        id=uuid4(),
        session_id=session_id,
        debate_id=debate_id,
        type=IntelligenceType.POST_DEBATE_FEEDBACK,
        team=Team.NEUTRAL,
        agent_role="user",
        content=content,
        confidence=1.0,
        scope="chat",
        created_at=datetime.now(timezone.utc),
    )
    await repo.insert(record)


@router.post("/api/sessions/{session_id}/debates/{debate_id}/verdict-review", status_code=204)
async def verdict_review(
    session_id: UUID,
    debate_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    from uuid import uuid4
    from core.schemas import IntelligenceRecord, IntelligenceType, Team
    repo = IntelligenceRepo(db)
    action = body.get("action", "")
    reason = body.get("reason", "")
    record = IntelligenceRecord(
        id=uuid4(),
        session_id=session_id,
        debate_id=debate_id,
        type=IntelligenceType.VERDICT_REVIEW,
        team=Team.NEUTRAL,
        agent_role="user",
        content=f"{action}: {reason}",
        confidence=1.0,
        scope="chat",
        created_at=datetime.now(timezone.utc),
    )
    await repo.insert(record)
