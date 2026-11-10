"""Conseil du jour Bien vieillir — lecture publique."""
import asyncio

from fastapi import APIRouter, HTTPException, Path, Query

from core import FRONTEND_URL, db
from daily_tips import generate_daily_tip, today_key

router = APIRouter(prefix="/tips", tags=["tips"])

_PUBLIC = {"_id": 0, "date_key": 1, "theme": 1, "title": 1, "text": 1, "action": 1}
DATE_RE = r"^\d{4}-\d{2}-\d{2}$"


def with_share(tip: dict | None) -> dict | None:
    if tip:
        tip["share_url"] = f"{FRONTEND_URL}/api/share/conseil/{tip['date_key']}"
        tip["page_url"] = f"{FRONTEND_URL}/conseils-bien-vieillir/{tip['date_key']}"
    return tip


@router.get("/today")
async def tip_today() -> dict:
    """Conseil du jour ; à défaut le plus récent (génération relancée en fond)."""
    key = today_key()
    tip = await db.daily_tips.find_one({"date_key": key}, _PUBLIC)
    if not tip:
        asyncio.create_task(generate_daily_tip(key))
        tip = await db.daily_tips.find_one({}, _PUBLIC, sort=[("date_key", -1)])
    return {"tip": with_share(tip), "is_today": bool(tip and tip["date_key"] == key)}


@router.get("/recent")
async def tips_recent(limit: int = Query(6, ge=1, le=366)) -> list[dict]:
    tips = await db.daily_tips.find({}, _PUBLIC).sort("date_key", -1).to_list(limit)
    return [with_share(t) for t in tips]


@router.get("/{date_key}")
async def tip_by_date(date_key: str = Path(..., pattern=DATE_RE)) -> dict:
    tip = await db.daily_tips.find_one({"date_key": date_key}, _PUBLIC)
    if not tip:
        raise HTTPException(status_code=404, detail="Conseil introuvable")
    return with_share(tip)
