"""Badges + Progression endpoints."""
from fastapi import APIRouter, Depends

from core import db, get_current_user
from progression import get_progression
from badges import get_user_badges, get_catalog_for_user

router = APIRouter(tags=["progression"])


@router.get("/progression/me")
async def my_progression(user: dict = Depends(get_current_user)) -> dict:
    """Full progression payload: level, xp progress, per-category mastery."""
    # Refresh the user doc to get the latest xp_total (avoid stale JWT cache)
    fresh = await db.users.find_one({"_id": user["_id"]}) or user
    return await get_progression(fresh)


@router.get("/badges/mine")
async def my_badges(user: dict = Depends(get_current_user)) -> list[dict]:
    """Return the user's earned badges (most recent first)."""
    return await get_user_badges(str(user["_id"]))


@router.get("/badges/catalog")
async def badge_catalog(user: dict = Depends(get_current_user)) -> list[dict]:
    """Full badge catalog with `earned` flag for the current user."""
    return await get_catalog_for_user(str(user["_id"]))
