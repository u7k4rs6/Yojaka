from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import UserDebateProfile
from storage.models import UserDebateProfileRow


def _row_to_profile(row: UserDebateProfileRow) -> UserDebateProfile:
    wins = json.loads(row.wins_json) if row.wins_json else {"pro": 0, "con": 0, "unclear": 0}
    side_history = json.loads(row.side_history_json) if row.side_history_json else {"pro": 0, "con": 0, "auto": 0}
    strengths = json.loads(row.strengths_json) if row.strengths_json else []
    weaknesses = json.loads(row.weaknesses_json) if row.weaknesses_json else []
    trainer_notes = json.loads(row.trainer_notes_json) if row.trainer_notes_json else []
    style_tags = json.loads(row.style_tags_json) if row.style_tags_json else []

    return UserDebateProfile(
        user_id=row.user_id,
        debates_completed=row.debates_completed or 0,
        practice_debates_completed=row.practice_debates_completed or 0,
        wins=wins,
        side_history=side_history,
        strengths=strengths,
        weaknesses=weaknesses,
        trainer_notes=trainer_notes,
        style_tags=style_tags,
        last_updated_at=row.last_updated_at,
    )


class UserProfileRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: str = "default") -> UserDebateProfile:
        result = await self.db.execute(
            select(UserDebateProfileRow).where(UserDebateProfileRow.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            # Create a fresh profile on first access
            row = UserDebateProfileRow(
                user_id=user_id,
                debates_completed=0,
                practice_debates_completed=0,
                wins_json=json.dumps({"pro": 0, "con": 0, "unclear": 0}),
                side_history_json=json.dumps({"pro": 0, "con": 0, "auto": 0}),
                strengths_json=json.dumps([]),
                weaknesses_json=json.dumps([]),
                trainer_notes_json=json.dumps([]),
                style_tags_json=json.dumps([]),
                last_updated_at=None,
            )
            self.db.add(row)
            await self.db.flush()
            await self.db.refresh(row)
        return _row_to_profile(row)

    async def update(self, profile: UserDebateProfile) -> UserDebateProfile:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(UserDebateProfileRow)
            .where(UserDebateProfileRow.user_id == profile.user_id)
            .values(
                debates_completed=profile.debates_completed,
                practice_debates_completed=profile.practice_debates_completed,
                wins_json=json.dumps(profile.wins),
                side_history_json=json.dumps(profile.side_history),
                strengths_json=json.dumps(profile.strengths),
                weaknesses_json=json.dumps(profile.weaknesses),
                trainer_notes_json=json.dumps(profile.trainer_notes),
                style_tags_json=json.dumps(profile.style_tags),
                last_updated_at=now,
            )
        )
        await self.db.flush()
        return await self.get(profile.user_id)

    async def reset(self, user_id: str = "default") -> None:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(UserDebateProfileRow).where(UserDebateProfileRow.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        await self.db.execute(
            update(UserDebateProfileRow)
            .where(UserDebateProfileRow.user_id == user_id)
            .values(
                debates_completed=0,
                practice_debates_completed=0,
                wins_json=json.dumps({"pro": 0, "con": 0, "unclear": 0}),
                side_history_json=json.dumps({"pro": 0, "con": 0, "auto": 0}),
                strengths_json=json.dumps([]),
                weaknesses_json=json.dumps([]),
                trainer_notes_json=json.dumps([]),
                style_tags_json=json.dumps([]),
                last_updated_at=now,
            )
        )
        await self.db.flush()
