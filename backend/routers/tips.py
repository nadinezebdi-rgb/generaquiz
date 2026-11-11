"""Conseil du jour Bien vieillir — lecture publique."""
import asyncio

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from datetime import datetime, timedelta

from fastapi import Depends

from core import FRONTEND_URL, db, get_current_user
from daily_tips import generate_daily_tip, today_key

router = APIRouter(prefix="/tips", tags=["tips"])

_PUBLIC = {"_id": 0, "date_key": 1, "theme": 1, "title": 1, "text": 1, "action": 1,
           "quiz.question": 1, "quiz.options": 1}
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


class TipAnswer(BaseModel):
    choice: int = Field(..., ge=0, le=3)


def _yesterday(key: str) -> str:
    return (datetime.strptime(key, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")


def _public_streak(st: dict | None) -> dict:
    st = st or {}
    key = today_key()
    # Série encore vivante si la dernière réponse date d'aujourd'hui ou d'hier
    count = int(st.get("count") or 0) if st.get("last_date") in (key, _yesterday(key)) else 0
    return {"count": count, "best": int(st.get("best") or 0), "last_date": st.get("last_date"),
            "last_result": st.get("last_result"), "answered_today": st.get("last_date") == key}


class StreakMerge(BaseModel):
    count: int = Field(..., ge=0, le=3660)
    best: int = Field(..., ge=0, le=3660)
    last_date: str = Field(..., pattern=DATE_RE)
    last_result: bool


@router.get("/streak/me")
async def streak_me(user: dict = Depends(get_current_user)) -> dict:
    return _public_streak(user.get("tip_streak"))


@router.post("/streak/answer")
async def streak_answer(body: TipAnswer, user: dict = Depends(get_current_user)) -> dict:
    """Met à jour la série du compte avec la réponse à la question DU JOUR (vérifiée ici)."""
    key = today_key()
    tip = await db.daily_tips.find_one({"date_key": key}, {"_id": 0, "quiz": 1})
    if not (tip or {}).get("quiz"):
        raise HTTPException(status_code=404, detail="Pas de question aujourd'hui")
    st = user.get("tip_streak") or {}
    if st.get("last_date") == key:
        return _public_streak(st)
    correct = body.choice == tip["quiz"]["correct_index"]
    prev = int(st.get("count") or 0) if st.get("last_date") == _yesterday(key) and st.get("last_result") else 0
    count = prev + 1 if correct else 0
    st = {"count": count, "best": max(int(st.get("best") or 0), count), "last_date": key, "last_result": correct}
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"tip_streak": st}})
    return _public_streak(st)


@router.post("/streak/merge")
async def streak_merge(body: StreakMerge, user: dict = Depends(get_current_user)) -> dict:
    """À la connexion : reprend la série de l'appareil si elle est plus récente/meilleure."""
    st = user.get("tip_streak") or {}
    key = today_key()
    if body.last_date > key:
        raise HTTPException(status_code=400, detail="Date invalide")
    device_live = body.last_date in (key, _yesterday(key)) and body.last_result
    account_live = st.get("last_date") in (key, _yesterday(key)) and st.get("last_result")
    take_device = device_live and (not account_live or body.count > int(st.get("count") or 0))
    new = dict(body.model_dump()) if take_device else dict(st)
    new["best"] = max(int(st.get("best") or 0), body.best, int(new.get("count") or 0))
    if new != st:
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"tip_streak": new}})
    return _public_streak(new)


@router.get("/{date_key}")
async def tip_by_date(date_key: str = Path(..., pattern=DATE_RE)) -> dict:
    tip = await db.daily_tips.find_one({"date_key": date_key}, _PUBLIC)
    if not tip:
        raise HTTPException(status_code=404, detail="Conseil introuvable")
    return with_share(tip)


@router.post("/{date_key}/answer")
async def tip_answer(body: TipAnswer, date_key: str = Path(..., pattern=DATE_RE)) -> dict:
    tip = await db.daily_tips.find_one({"date_key": date_key}, {"_id": 0, "quiz": 1})
    quiz = (tip or {}).get("quiz")
    if not quiz:
        raise HTTPException(status_code=404, detail="Question introuvable")
    return {"correct": body.choice == quiz["correct_index"], "correct_index": quiz["correct_index"],
            "explanation": quiz["explanation"]}
