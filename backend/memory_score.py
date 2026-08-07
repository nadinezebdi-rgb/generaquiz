"""Score Mémoire — 5 axes cognitifs.

Chaque axe est un score 0-100 déduit des collections existantes
(attempts, daily_attempts, coop_challenges, user_category_stats, users).
Aucune donnée n'est stockée : le score est recalculé à la demande —
simple, transparent, jamais désynchronisé.

Axes:
  - culture     — précision globale sur les quiz par catégorie
  - regularite  — assiduité (jours joués sur les 30 derniers jours + streak)
  - attention   — précision sur le Quiz du Jour (mesure de concentration)
  - rapidite    — temps moyen par question (faster is better)
  - memoire     — maîtrise cumulée par catégorie (novice → maître)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from core import db


AXES = [
    {"key": "culture",    "label": "Culture",    "hint": "Précision sur vos quiz par catégorie"},
    {"key": "regularite", "label": "Régularité", "hint": "Jours joués & série en cours"},
    {"key": "attention",  "label": "Attention",  "hint": "Précision sur le Quiz du Jour"},
    {"key": "rapidite",   "label": "Rapidité",   "hint": "Temps moyen par question"},
    {"key": "memoire",    "label": "Mémoire",    "hint": "Maîtrise cumulée par catégorie"},
]

# Anti-cheese thresholds : below the minimum sample we return a "cold start"
# score instead of a misleading 100% on a single attempt.
COLD_START_ATTEMPTS = 3         # quiz par catégorie
COLD_START_DAILY = 3            # quiz du jour
COLD_START_TIMED = 5            # attempts avec duration_seconds

# Seconds/question benchmarks — a lucid answer sits around 8-15 s.
SPEED_FAST_S = 6.0    # ≤ 6 s → 100 pts
SPEED_SLOW_S = 25.0   # ≥ 25 s → 0 pt


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


async def _axis_culture(user_id: str) -> tuple[int, dict]:
    agg = await db.attempts.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "score": {"$sum": "$score"},
            "total": {"$sum": "$total"},
            "n": {"$sum": 1},
        }},
    ]).to_list(1)
    if not agg:
        return 0, {"attempts": 0, "correct": 0, "total": 0}
    n = int(agg[0]["n"])
    s = int(agg[0]["score"])
    t = int(agg[0]["total"])
    if n < COLD_START_ATTEMPTS:
        # Return the accuracy but flag it as low-confidence
        pct = (s / t * 100) if t else 0
        return _clamp(pct * (n / COLD_START_ATTEMPTS)), {"attempts": n, "correct": s, "total": t, "cold_start": True}
    return _clamp((s / t) * 100 if t else 0), {"attempts": n, "correct": s, "total": t}


async def _axis_regularite(user_id: str, user_doc: dict) -> tuple[int, dict]:
    """Days played in the last 30 (attempts + daily) + streak boost."""
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    # unique dates from attempts
    dates_a = await db.attempts.distinct(
        "created_at", {"user_id": user_id, "created_at": {"$gte": since}}
    )
    # unique daily_attempts date_keys (already YYYY-MM-DD)
    dates_d = await db.daily_attempts.distinct(
        "date_key", {"user_id": user_id, "date_key": {"$gte": (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")}}
    )
    days = set(dates_d)
    for iso in dates_a:
        # keep only the YYYY-MM-DD part
        if isinstance(iso, str) and len(iso) >= 10:
            days.add(iso[:10])

    days_count = len(days)
    streak_current = int(user_doc.get("streak_current") or 0)
    # 20 days / 30 → 100 pts baseline, streak adds a small bonus
    baseline = (days_count / 20) * 100
    streak_bonus = min(20, streak_current * 2)  # streak of 10 → +20
    score = _clamp(baseline + streak_bonus)
    return score, {
        "days_played_last_30": days_count,
        "streak_current": streak_current,
    }


async def _axis_attention(user_id: str) -> tuple[int, dict]:
    docs = await db.daily_attempts.find(
        {"user_id": user_id}, {"_id": 0, "score": 1, "total": 1},
    ).to_list(200)
    if not docs:
        return 0, {"daily_played": 0, "correct": 0, "total": 0}
    n = len(docs)
    s = sum(int(d.get("score", 0)) for d in docs)
    t = sum(int(d.get("total", 0)) for d in docs)
    pct = (s / t * 100) if t else 0
    if n < COLD_START_DAILY:
        return _clamp(pct * (n / COLD_START_DAILY)), {"daily_played": n, "correct": s, "total": t, "cold_start": True}
    return _clamp(pct), {"daily_played": n, "correct": s, "total": t}


async def _axis_rapidite(user_id: str) -> tuple[int, dict]:
    docs = await db.attempts.find(
        {"user_id": user_id, "duration_seconds": {"$gt": 0}},
        {"_id": 0, "duration_seconds": 1, "total": 1},
    ).to_list(300)
    n = len(docs)
    if n < COLD_START_TIMED:
        return 0, {"timed_attempts": n, "avg_sec_per_question": None, "cold_start": True}
    total_sec = sum(float(d["duration_seconds"]) for d in docs)
    total_q = sum(int(d.get("total") or 0) for d in docs) or 1
    avg = total_sec / total_q
    if avg <= SPEED_FAST_S:
        score = 100.0
    elif avg >= SPEED_SLOW_S:
        score = 0.0
    else:
        score = (SPEED_SLOW_S - avg) / (SPEED_SLOW_S - SPEED_FAST_S) * 100
    return _clamp(score), {"timed_attempts": n, "avg_sec_per_question": round(avg, 1)}


async def _axis_memoire(user_id: str) -> tuple[int, dict]:
    """Aggregated mastery across categories — weighted by volume played."""
    stats = await db.user_category_stats.find(
        {"user_id": user_id}, {"_id": 0, "correct": 1, "total": 1},
    ).to_list(50)
    total_correct = sum(int(s.get("correct", 0)) for s in stats)
    total_total = sum(int(s.get("total", 0)) for s in stats)
    n_cats = len([s for s in stats if int(s.get("total", 0)) > 0])
    if total_total == 0:
        return 0, {"categories_played": 0, "correct": 0, "total": 0}
    # Reward players who have engaged with multiple categories.
    breadth_multiplier = min(1.0, n_cats / 4)  # need 4+ categories for full breadth
    accuracy = total_correct / total_total * 100
    return _clamp(accuracy * (0.6 + 0.4 * breadth_multiplier)), {
        "categories_played": n_cats,
        "correct": total_correct,
        "total": total_total,
    }


async def compute_memory_score(user: dict) -> dict:
    """Return {axes: [{key, label, hint, value, detail}], overall, computed_at}.

    All 5 axes always present, in canonical order.
    """
    user_id = str(user["_id"])
    culture, culture_d = await _axis_culture(user_id)
    regularite, reg_d = await _axis_regularite(user_id, user)
    attention, att_d = await _axis_attention(user_id)
    rapidite, rap_d = await _axis_rapidite(user_id)
    memoire, mem_d = await _axis_memoire(user_id)

    scores = {
        "culture": (culture, culture_d),
        "regularite": (regularite, reg_d),
        "attention": (attention, att_d),
        "rapidite": (rapidite, rap_d),
        "memoire": (memoire, mem_d),
    }
    axes: list[dict[str, Any]] = []
    for a in AXES:
        v, d = scores[a["key"]]
        axes.append({**a, "value": int(v), "detail": d})
    overall = _clamp(sum(a["value"] for a in axes) / len(axes))
    return {
        "axes": axes,
        "overall": overall,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
