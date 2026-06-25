"""Public stats router — anonymous, no-auth, used by the landing page.

Endpoints:
  GET /api/stats/public — aggregated counters for the "En chiffres" section
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter

from core import db

router = APIRouter(prefix="/stats", tags=["stats"])

PARIS_TZ = ZoneInfo("Europe/Paris")


def _today_key() -> str:
    return datetime.now(PARIS_TZ).strftime("%Y-%m-%d")


@router.get("/public")
async def public_stats() -> dict:
    """Aggregated public counters (no auth, cached by reverse proxy in front).

    Returns:
        players_today: distinct users who played a quiz (any kind) today
        games_today: count of attempts inserted in the last 24h
        games_total: lifetime attempts
        questions_total: questions currently in the catalog
        streak_record: highest streak_best across all users
        countries_active: distinct country_code values across users
    """
    today = _today_key()
    now_utc = datetime.now(timezone.utc)
    last_24h_iso = (now_utc - timedelta(hours=24)).isoformat()

    # Distinct players today (daily_quiz + category attempts)
    daily_player_ids: set[str] = set()
    async for d in db.daily_attempts.find({"date_key": today}, {"user_id": 1, "_id": 0}):
        daily_player_ids.add(d["user_id"])
    async for a in db.attempts.find(
        {"created_at": {"$gte": today + "T00:00:00"}},
        {"user_id": 1, "_id": 0},
    ):
        daily_player_ids.add(a["user_id"])
    players_today = len(daily_player_ids)

    games_today = await db.attempts.count_documents({"created_at": {"$gte": last_24h_iso}})
    games_today += await db.daily_attempts.count_documents({"date_key": today})

    games_total = await db.attempts.count_documents({})
    games_total += await db.daily_attempts.count_documents({})

    questions_total = await db.questions.count_documents({})

    streak_record_doc = await db.users.find(
        {"streak_best": {"$exists": True, "$gt": 0}},
        {"streak_best": 1, "_id": 0},
    ).sort("streak_best", -1).limit(1).to_list(1)
    streak_record = int(streak_record_doc[0]["streak_best"]) if streak_record_doc else 0

    # Distinct country codes (defaults to FR — countries are recorded at register
    # from the Accept-Language header). Falls back to 1 if no codes stored.
    countries = await db.users.distinct("country_code", {"country_code": {"$ne": None}})
    countries_active = max(1, len(countries))

    return {
        "players_today": players_today,
        "games_today": games_today,
        "games_total": games_total,
        "questions_total": questions_total,
        "streak_record": streak_record,
        "countries_active": countries_active,
        "updated_at": now_utc.isoformat(),
    }
