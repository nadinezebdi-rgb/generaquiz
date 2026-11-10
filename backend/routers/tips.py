"""Conseil du jour Bien vieillir — lecture publique."""
import asyncio

from fastapi import APIRouter, Query

from core import db
from daily_tips import generate_daily_tip, today_key

router = APIRouter(prefix="/tips", tags=["tips"])

_PUBLIC = {"_id": 0, "date_key": 1, "theme": 1, "title": 1, "text": 1, "action": 1}


@router.get("/today")
async def tip_today() -> dict:
    """Conseil du jour ; à défaut le plus récent (génération relancée en fond)."""
    key = today_key()
    tip = await db.daily_tips.find_one({"date_key": key}, _PUBLIC)
    if not tip:
        asyncio.create_task(generate_daily_tip(key))
        tip = await db.daily_tips.find_one({}, _PUBLIC, sort=[("date_key", -1)])
    return {"tip": tip, "is_today": bool(tip and tip["date_key"] == key)}


@router.get("/recent")
async def tips_recent(limit: int = Query(6, ge=1, le=30)) -> list[dict]:
    return await db.daily_tips.find({}, _PUBLIC).sort("date_key", -1).to_list(limit)
