"""Solo progression: user levels + category mastery.

**Level curve** — a quadratic thresholds table so early levels feel fast,
late levels feel rewarding. Formula: xp_for_level(L) = 25 * L * (L+1).

  Level 1  →      50 XP
  Level 2  →     150 XP
  Level 5  →     750 XP
  Level 10 →   2 750 XP
  Level 20 →  10 500 XP
  Level 50 →  63 750 XP

**Mastery** — per (user, category): tally correct + total, expose ratio
and a coarse tier (novice → apprenti → confirmé → expert → maître).
Stored in `user_category_stats` (upsert on every attempt).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from core import db


def xp_for_level(level: int) -> int:
    """Cumulative XP required to REACH `level` (level ≥ 1). Level 1 = 0 XP."""
    if level <= 1:
        return 0
    return 25 * (level - 1) * level


def compute_level(xp_total: int) -> dict:
    """Given raw xp_total, return {level, xp_in_level, xp_to_next, progress_pct}.

    We solve the inverse of xp_for_level(L) numerically (small ceiling — no
    users will realistically hit Level 500 in this app's lifetime)."""
    xp = max(0, int(xp_total or 0))
    level = 1
    while xp >= xp_for_level(level + 1) and level < 500:
        level += 1
    floor = xp_for_level(level)
    ceil_ = xp_for_level(level + 1)
    span = max(1, ceil_ - floor)
    in_level = xp - floor
    progress = round(100 * in_level / span)
    return {
        "level": level,
        "xp_total": xp,
        "xp_in_level": in_level,
        "xp_to_next": max(0, ceil_ - xp),
        "next_level_at": ceil_,
        "progress_pct": min(100, max(0, progress)),
    }


# ---------------------------------------------------------------------------
# Category mastery
# ---------------------------------------------------------------------------

MASTERY_TIERS = [
    # (min_total, min_ratio, key,        label)
    (200, 0.90, "maitre",   "Maître"),
    (100, 0.80, "expert",   "Expert"),
    (50,  0.70, "confirme", "Confirmé"),
    (20,  0.0,  "apprenti", "Apprenti"),
    (0,   0.0,  "novice",   "Novice"),
]


def _tier_for(correct: int, total: int) -> dict:
    ratio = (correct / total) if total else 0.0
    for min_total, min_ratio, key, label in MASTERY_TIERS:
        if total >= min_total and ratio >= min_ratio:
            return {"key": key, "label": label, "ratio_pct": round(ratio * 100)}
    return {"key": "novice", "label": "Novice", "ratio_pct": round(ratio * 100)}


async def record_category_mastery(user_id: str, category_id: str, correct: int, total: int) -> dict:
    """Upsert `user_category_stats` and return the fresh cumulative stats.

    Called from POST /attempts once the server-authoritative score is known.
    """
    now = datetime.now(timezone.utc).isoformat()
    res = await db.user_category_stats.find_one_and_update(
        {"user_id": user_id, "category_id": category_id},
        {
            "$inc": {"correct": int(correct), "total": int(total), "quizzes_played": 1},
            "$set": {"updated_at": now},
            "$setOnInsert": {"user_id": user_id, "category_id": category_id, "created_at": now},
        },
        upsert=True,
        return_document=True,
    )
    if not res:  # returning-doc quirk in some Motor versions
        res = await db.user_category_stats.find_one({"user_id": user_id, "category_id": category_id})
    return {
        "category_id": category_id,
        "correct": int(res.get("correct", 0)),
        "total": int(res.get("total", 0)),
        "quizzes_played": int(res.get("quizzes_played", 0)),
        "tier": _tier_for(int(res.get("correct", 0)), int(res.get("total", 0))),
    }


async def get_progression(user: dict) -> dict:
    """Return the full progression payload used by GET /api/progression/me."""
    xp = int(user.get("xp_total") or 0)
    level_info = compute_level(xp)
    user_id = str(user["_id"])
    mastery: list[dict] = []
    cats = await db.categories.find({}, {"_id": 0, "id": 1, "title": 1, "mascot_image": 1, "mascot_name": 1}).to_list(50)
    stats_docs = await db.user_category_stats.find(
        {"user_id": user_id}, {"_id": 0},
    ).to_list(50)
    by_cat = {s["category_id"]: s for s in stats_docs}
    for c in cats:
        s = by_cat.get(c["id"], {})
        correct = int(s.get("correct", 0))
        total = int(s.get("total", 0))
        mastery.append({
            "category_id": c["id"],
            "title": c["title"],
            "mascot_image": c.get("mascot_image"),
            "mascot_name": c.get("mascot_name"),
            "correct": correct,
            "total": total,
            "quizzes_played": int(s.get("quizzes_played", 0)),
            "tier": _tier_for(correct, total),
        })
    return {**level_info, "mastery": mastery}
