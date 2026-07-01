"""Badges: persistent achievements catalog + awarding helper.

Design:
  - Static `BADGES` catalog (id, title, description, emoji, tier, criteria hint)
  - `user_badges` collection stores earned badges (unique idx on user_id+badge_id)
  - `award_badge(user_id, badge_id, meta?)` is IDEMPOTENT — silently no-op if
    already earned; returns True if newly awarded (so the API response can
    trigger a client-side toast).
  - Check hooks live at the callsite (attempts, coop, referral, ligues).

Kept intentionally simple — no rules engine, no cron sweeps. Every event
that could award a badge calls `award_*_if_eligible(user)` in-line.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from core import db, logger

# ---------------------------------------------------------------------------
# Static catalog — the source of truth for badge metadata.
# ---------------------------------------------------------------------------
BADGES: list[dict] = [
    # -- Getting started --
    {"id": "first_quiz",       "title": "Premier pas",        "desc": "Terminer votre 1ᵉʳ quiz",             "emoji": "🎯", "tier": "bronze",  "family": "starter"},
    {"id": "first_coop",       "title": "Duo formé",          "desc": "Terminer votre 1ᵉʳ défi coopératif",  "emoji": "🤝", "tier": "bronze",  "family": "coop"},
    # -- Streaks --
    {"id": "streak_3",         "title": "Petite flamme",      "desc": "3 jours consécutifs",                 "emoji": "🔥", "tier": "bronze",  "family": "streak"},
    {"id": "streak_7",         "title": "Feu de camp",        "desc": "7 jours consécutifs",                 "emoji": "🔥", "tier": "argent",  "family": "streak"},
    {"id": "streak_30",        "title": "Brasier",            "desc": "30 jours consécutifs",                "emoji": "🔥", "tier": "or",      "family": "streak"},
    {"id": "streak_100",       "title": "Incandescent",       "desc": "100 jours consécutifs",               "emoji": "🌟", "tier": "diamant", "family": "streak"},
    # -- Daily --
    {"id": "daily_perfect",    "title": "Sans-faute",         "desc": "5/5 au Quiz du Jour",                 "emoji": "✅", "tier": "argent",  "family": "daily"},
    {"id": "daily_speed",      "title": "Éclair",             "desc": "5/5 en moins de 30 secondes",         "emoji": "⚡", "tier": "or",      "family": "daily"},
    {"id": "early_bird",       "title": "Lève-tôt",           "desc": "Quiz du Jour terminé avant 9h",       "emoji": "🐦", "tier": "argent",  "family": "daily"},
    # -- Coop --
    {"id": "coop_5",           "title": "Complice",           "desc": "5 défis coop terminés",               "emoji": "👥", "tier": "argent",  "family": "coop"},
    {"id": "coop_saviour",     "title": "Sauveur de l'Ancre", "desc": "10 aides réussies en coop",           "emoji": "🛟", "tier": "or",      "family": "coop"},
    # -- League --
    {"id": "league_promoted",  "title": "Ascension",          "desc": "Promu de ligue",                       "emoji": "🚀", "tier": "argent",  "family": "league"},
    {"id": "league_diamond",   "title": "Ligue Diamant",      "desc": "Atteindre la Ligue Diamant",           "emoji": "💎", "tier": "diamant", "family": "league"},
    # -- Referral / social --
    {"id": "referrer_1",       "title": "Bon voisin",         "desc": "1 filleul actif",                     "emoji": "💌", "tier": "argent",  "family": "social"},
    {"id": "referrer_5",       "title": "Ambassadeur",        "desc": "5 filleuls actifs",                   "emoji": "📢", "tier": "or",      "family": "social"},
]
BADGE_INDEX = {b["id"]: b for b in BADGES}


# ---------------------------------------------------------------------------
# Awarding helper — used by all in-line check callers below.
# ---------------------------------------------------------------------------
async def award_badge(user_id: str, badge_id: str, meta: Optional[dict] = None) -> bool:
    """Idempotently grant a badge. Returns True if newly awarded."""
    if badge_id not in BADGE_INDEX:
        logger.warning(f"[badges] unknown badge_id={badge_id}")
        return False
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "user_id": user_id,
        "badge_id": badge_id,
        "earned_at": now,
    }
    if meta:
        doc["meta"] = meta
    try:
        await db.user_badges.insert_one(doc)
        return True
    except Exception:
        # DuplicateKeyError → already earned. Not an error.
        return False


async def get_user_badges(user_id: str) -> list[dict]:
    """Return the user's earned badges enriched with catalog metadata."""
    rows = await db.user_badges.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    enriched = []
    for r in rows:
        meta = BADGE_INDEX.get(r["badge_id"])
        if not meta:
            continue
        enriched.append({**meta, "earned_at": r["earned_at"]})
    enriched.sort(key=lambda x: x["earned_at"], reverse=True)
    return enriched


async def get_catalog_for_user(user_id: str) -> list[dict]:
    """All badges + earned flag/date, useful for the collection page."""
    earned_rows = await db.user_badges.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    earned_map = {r["badge_id"]: r["earned_at"] for r in earned_rows}
    return [
        {**b, "earned": b["id"] in earned_map, "earned_at": earned_map.get(b["id"])}
        for b in BADGES
    ]


# ---------------------------------------------------------------------------
# Event-driven eligibility checks — called from the routers.
# Each returns the list of NEWLY awarded badge_ids so the caller can echo
# them in the HTTP response and the client can pop a toast.
# ---------------------------------------------------------------------------
async def check_after_attempt(user: dict, score: int, total: int) -> list[str]:
    """Called from POST /api/attempts after the server-authoritative score
    has been computed and persisted."""
    awarded: list[str] = []
    user_id = str(user["_id"])
    # first_quiz — first ever attempt
    prev = await db.attempts.count_documents({"user_id": user_id})
    if prev <= 1:  # the current attempt is already inserted
        if await award_badge(user_id, "first_quiz"):
            awarded.append("first_quiz")
    return awarded


async def check_after_daily(user: dict, score: int, total: int, duration_seconds: int, hour_paris: int, streak: int) -> list[str]:
    """Called from POST /api/daily/submit."""
    awarded: list[str] = []
    user_id = str(user["_id"])
    if score == total and total > 0:
        if await award_badge(user_id, "daily_perfect"):
            awarded.append("daily_perfect")
        if duration_seconds and duration_seconds < 30:
            if await award_badge(user_id, "daily_speed"):
                awarded.append("daily_speed")
    if 0 <= hour_paris < 9:
        if await award_badge(user_id, "early_bird"):
            awarded.append("early_bird")
    for threshold, badge_id in [(3, "streak_3"), (7, "streak_7"), (30, "streak_30"), (100, "streak_100")]:
        if streak >= threshold:
            if await award_badge(user_id, badge_id):
                awarded.append(badge_id)
    return awarded


async def check_after_coop_completed(user: dict, stats_coop: dict) -> list[str]:
    """Called at the end of a coop challenge (completed=True)."""
    awarded: list[str] = []
    user_id = str(user["_id"])
    completed_count = await db.coop_challenges.count_documents(
        {"creator_user_id": user_id, "status": "completed"},
    )
    if completed_count >= 1:
        if await award_badge(user_id, "first_coop"):
            awarded.append("first_coop")
    if completed_count >= 5:
        if await award_badge(user_id, "coop_5"):
            awarded.append("coop_5")
    # Sum lifetime helps_successful across all coop challenges
    cursor = db.coop_challenges.aggregate([
        {"$match": {"creator_user_id": user_id, "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$stats_coop.helps_successful"}}},
    ])
    total_helps = 0
    async for row in cursor:
        total_helps = int(row.get("total") or 0)
    if total_helps >= 10:
        if await award_badge(user_id, "coop_saviour"):
            awarded.append("coop_saviour")
    return awarded


async def check_after_referral(referrer_id: str) -> list[str]:
    """Called from grant_referral_bonus_if_eligible after crediting the referrer."""
    awarded: list[str] = []
    from bson import ObjectId
    try:
        referrer = await db.users.find_one({"_id": ObjectId(referrer_id)}, {"referral_count": 1})
    except Exception:
        return awarded
    count = int((referrer or {}).get("referral_count") or 0)
    if count >= 1 and await award_badge(referrer_id, "referrer_1"):
        awarded.append("referrer_1")
    if count >= 5 and await award_badge(referrer_id, "referrer_5"):
        awarded.append("referrer_5")
    return awarded


async def check_after_league_settle(user_id: str, new_tier: str, promoted: bool) -> list[str]:
    """Called from settle_finished_week for each user whose tier changed."""
    awarded: list[str] = []
    if promoted:
        if await award_badge(user_id, "league_promoted"):
            awarded.append("league_promoted")
    if new_tier == "diamant":
        if await award_badge(user_id, "league_diamond"):
            awarded.append("league_diamond")
    return awarded
