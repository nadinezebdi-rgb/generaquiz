"""Quiz du Jour — daily challenge with deterministic question selection and leaderboard.

- Same 5 questions for everyone each calendar day (Europe/Paris).
- Playable WITHOUT account (frontend tracks score locally).
- Submitting score requires auth; one submission per user per day.
- Leaderboard: top 10 of the day + current user rank if authenticated.
"""
import hashlib
import random
from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core import db, get_current_user, JWT_SECRET, JWT_ALG, logger

router = APIRouter(tags=["daily"])

DAILY_QUESTION_COUNT = 5
PARIS_TZ = ZoneInfo("Europe/Paris")


# -------------------- helpers --------------------
def _today_key() -> str:
    """YYYY-MM-DD in Europe/Paris (DST-aware via zoneinfo)."""
    return datetime.now(PARIS_TZ).strftime("%Y-%m-%d")


async def _optional_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if payload.get("type") != "access":
            return None
        u = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        return dict(u) if u else None
    except Exception:
        return None


async def _pick_daily_questions(date_key: str) -> list[dict]:
    """Deterministic 5-question pick mixing categories. Same for everyone on a given day."""
    seed = int(hashlib.sha256(date_key.encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)

    cat_ids = [c["id"] for c in await db.categories.find({}, {"_id": 0, "id": 1}).to_list(50)]
    rng.shuffle(cat_ids)
    chosen_cats = cat_ids[:DAILY_QUESTION_COUNT]

    picked: list[dict] = []
    for cat_id in chosen_cats:
        qs = await db.questions.find({"category_id": cat_id}, {"_id": 0}).to_list(200)
        if not qs:
            continue
        picked.append(rng.choice(qs))
    # Fallback: top up from any category if we have less than DAILY_QUESTION_COUNT
    if len(picked) < DAILY_QUESTION_COUNT:
        all_qs = await db.questions.find({}, {"_id": 0}).to_list(2000)
        rng.shuffle(all_qs)
        for q in all_qs:
            if q not in picked:
                picked.append(q)
            if len(picked) >= DAILY_QUESTION_COUNT:
                break
    return picked[:DAILY_QUESTION_COUNT]


# In-memory cache to avoid hitting MongoDB for every daily-quiz request and every
# morning email send. Keyed by date_key; auto-evicts on day rollover.
_daily_cache: dict[str, list[dict]] = {}


async def get_daily_questions_cached(date_key: str) -> list[dict]:
    """Cached wrapper around _pick_daily_questions. Same for everyone on a given day."""
    cached = _daily_cache.get(date_key)
    if cached is not None:
        return cached
    # On a new day, drop stale entries (small dict but keep it tidy)
    if _daily_cache:
        _daily_cache.clear()
    picked = await _pick_daily_questions(date_key)
    _daily_cache[date_key] = picked
    return picked


# -------------------- request models --------------------
class DailySubmit(BaseModel):
    score: int = Field(..., ge=0, le=DAILY_QUESTION_COUNT)
    duration_seconds: Optional[int] = Field(None, ge=0, le=3600)


# -------------------- endpoints --------------------
@router.get("/daily/quiz")
async def get_daily_quiz(request: Request):
    """Public endpoint: returns today's 5 questions (deterministic per day).

    If user is authenticated, also returns `has_played` (already submitted today).
    """
    date_key = _today_key()
    questions = await get_daily_questions_cached(date_key)
    user = await _optional_user(request)
    has_played = False
    if user:
        existing = await db.daily_attempts.find_one({
            "user_id": str(user["_id"]),
            "date_key": date_key,
        })
        has_played = bool(existing)
    return {
        "date": date_key,
        "questions": questions,
        "count": len(questions),
        "has_played": has_played,
        "is_authenticated": user is not None,
    }


@router.post("/daily/submit")
async def submit_daily(body: DailySubmit, user: dict = Depends(get_current_user)):
    """Save the user's daily score, update streak. One submission per user per day."""
    date_key = _today_key()
    user_id = str(user["_id"])
    existing = await db.daily_attempts.find_one({"user_id": user_id, "date_key": date_key})
    if existing:
        raise HTTPException(status_code=409, detail="Vous avez déjà joué le Quiz du Jour aujourd'hui.")

    # --- streak computation ---
    last_date = user.get("streak_last_date")
    current = int(user.get("streak_current") or 0)
    best = int(user.get("streak_best") or 0)
    today = date_key
    yesterday = (datetime.now(PARIS_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
    if last_date == yesterday:
        current += 1                       # streak continues
    elif last_date == today:
        current = max(current, 1)          # already counted today (shouldn't happen due to 409 above)
    else:
        current = 1                        # streak reset / start
    if current > best:
        best = current
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "streak_current": current,
            "streak_best": best,
            "streak_last_date": today,
        }},
    )

    doc = {
        "user_id": user_id,
        "user_name": user.get("name") or user.get("email", "").split("@")[0],
        "date_key": date_key,
        "score": body.score,
        "total": DAILY_QUESTION_COUNT,
        "duration_seconds": body.duration_seconds or 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.daily_attempts.insert_one(doc)

    # Award XP toward the user's weekly league cohort (lazy import to avoid cycles)
    try:
        from core import XP_PER_CORRECT_DAILY
        from routers.gamification import _ensure_league_membership, _week_key
        xp_gained = body.score * XP_PER_CORRECT_DAILY
        if xp_gained > 0:
            await _ensure_league_membership(user_id)
            await db.league_scores.update_one(
                {"user_id": user_id, "week_key": _week_key()},
                {"$inc": {"xp": xp_gained}, "$setOnInsert": {
                    "user_id": user_id, "week_key": _week_key(),
                    "user_name": user.get("name") or user.get("email", "").split("@")[0],
                }},
                upsert=True,
            )
            await db.users.update_one({"_id": user["_id"]}, {"$inc": {"xp_total": xp_gained}})
    except Exception as e:  # never block the daily submit
        logger.warning(f"[daily] XP award failed: {e}")

    return {
        "ok": True,
        "saved": True,
        "streak_current": current,
        "streak_best": best,
    }


@router.get("/daily/leaderboard")
async def daily_leaderboard(request: Request):
    """Top 10 scores of the day (sorted by score desc, then duration asc, then created_at asc).

    If authenticated, also returns the user's own rank/score for the day.
    """
    date_key = _today_key()
    user = await _optional_user(request)

    top = await db.daily_attempts.find(
        {"date_key": date_key},
        {"_id": 0, "user_id": 0},
    ).sort([("score", -1), ("duration_seconds", 1), ("created_at", 1)]).to_list(10)

    total_players = await db.daily_attempts.count_documents({"date_key": date_key})

    my_entry = None
    my_rank = None
    if user:
        mine = await db.daily_attempts.find_one(
            {"user_id": str(user["_id"]), "date_key": date_key},
            {"_id": 0},
        )
        if mine:
            # Rank = 1 + number of attempts strictly better than mine.
            better = await db.daily_attempts.count_documents({
                "date_key": date_key,
                "$or": [
                    {"score": {"$gt": mine["score"]}},
                    {"score": mine["score"], "duration_seconds": {"$lt": mine["duration_seconds"]}},
                ],
            })
            my_rank = better + 1
            my_entry = {
                "user_name": mine["user_name"],
                "score": mine["score"],
                "total": mine["total"],
                "duration_seconds": mine["duration_seconds"],
            }

    return {
        "date": date_key,
        "top": top,
        "total_players": total_players,
        "my_rank": my_rank,
        "my_entry": my_entry,
    }
