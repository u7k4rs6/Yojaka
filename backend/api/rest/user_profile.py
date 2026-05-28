from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas import AgentExperience
from repositories.user_profile_repo import UserProfileRepo
from repositories.agent_experience_repo import AgentExperienceRepo
from storage.database import get_db

router = APIRouter(prefix="/api")


@router.get("/user-debate-profile")
async def get_user_profile(db: AsyncSession = Depends(get_db)):
    repo = UserProfileRepo(db)
    profile = await repo.get("default")
    return profile.model_dump()


@router.get("/user-debate-profile/overview")
async def get_user_profile_overview(db: AsyncSession = Depends(get_db)):
    repo = UserProfileRepo(db)
    profile = await repo.get("default")
    return {
        "debates_completed":          profile.debates_completed,
        "practice_debates_completed": profile.practice_debates_completed,
        "wins":                       profile.wins,
        "strengths":                  profile.strengths[:5],
        "weaknesses":                 profile.weaknesses[:5],
        "style_tags":                 profile.style_tags,
    }


@router.post("/user-debate-profile/reset", status_code=204)
async def reset_user_profile(body: dict, db: AsyncSession = Depends(get_db)):
    confirmation = body.get("confirmation") or body.get("confirm", "")
    if confirmation != "RESET USER DEBATE PROFILE":
        raise HTTPException(status_code=400, detail="Invalid confirmation phrase")
    repo = UserProfileRepo(db)
    await repo.reset("default")


@router.get("/ai-debater-experiences")
async def get_ai_debater_experiences(db: AsyncSession = Depends(get_db)):
    repo = AgentExperienceRepo(db)
    # Fetch a sample from each archetype
    from core.schemas import Archetype
    result = {}
    for arch in Archetype:
        experiences = await repo.fetch_by_archetype(arch.value, limit=3)
        result[arch.value] = [e.model_dump() for e in experiences]
    return result
