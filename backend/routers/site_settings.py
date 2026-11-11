"""Réglages du site pilotables depuis l'admin (collection `site_settings`)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core import db, get_admin_user, record_audit

router = APIRouter(tags=["site-settings"])

STATS_KEY = "public_stats_thresholds"
DEFAULT_STATS_THRESHOLDS = {"players_today": 20, "games_today": 50, "countries_active": 3, "streak_record": 7}


async def get_stats_thresholds() -> dict:
    doc = await db.site_settings.find_one({"key": STATS_KEY}, {"_id": 0, "value": 1}) or {}
    return {**DEFAULT_STATS_THRESHOLDS, **(doc.get("value") or {})}


class StatsThresholds(BaseModel):
    players_today: int = Field(..., ge=0, le=1_000_000)
    games_today: int = Field(..., ge=0, le=1_000_000)
    countries_active: int = Field(..., ge=0, le=300)
    streak_record: int = Field(..., ge=0, le=10_000)


@router.get("/admin/site-settings/stats")
async def admin_get_stats_thresholds(admin: dict = Depends(get_admin_user)) -> dict:
    return await get_stats_thresholds()


@router.put("/admin/site-settings/stats")
async def admin_set_stats_thresholds(body: StatsThresholds, admin: dict = Depends(get_admin_user)) -> dict:
    value = body.model_dump()
    await db.site_settings.update_one({"key": STATS_KEY}, {"$set": {"key": STATS_KEY, "value": value}}, upsert=True)
    await record_audit(admin, action="site.stats_thresholds", target_type="system", meta=value)
    return value
