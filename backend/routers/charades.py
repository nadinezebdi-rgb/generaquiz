"""Charades router — server-side scored word game.

Endpoints
---------
GET  /charades/list          → list of {id, parts[], hint} (no answer leaked!)
POST /charades/attempt       → validate a single attempt, return correct/expected + points
GET  /charades/progress      → user's stats: solved_count, best_streak, mastered_ids
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_current_user
from badges import award_badge, BADGE_INDEX
from charades_data import CHARADES, PACKS, charades_for_pack, normalize


router = APIRouter(prefix="/charades", tags=["charades"])


# Reward tuning
POINTS_PER_CORRECT = 5
BADGE_AT_SOLVED = 10   # unlock "Amateur de mots" after 10 solved


class AttemptIn(BaseModel):
    charade_id: str
    answer: str = Field(..., min_length=1, max_length=80)


def _public_charade(c: dict) -> dict:
    """Strip the answer before sending to the client."""
    return {
        "id": c["id"],
        "pack": c["pack"],
        "parts": c["parts"],
        "hint": c["hint"],
    }


@router.get("/packs")
async def list_packs(user: dict = Depends(get_current_user)) -> list[dict]:
    """Pack catalog with counts (solved / total per pack)."""
    user_id = str(user["_id"])
    solved = set(await db.charade_attempts.distinct(
        "charade_id", {"user_id": user_id, "correct": True}
    ))
    out = []
    for p in PACKS:
        pack_charades = [c for c in CHARADES if c["pack"] == p["id"]]
        out.append({
            **p,
            "total": len(pack_charades),
            "solved": sum(1 for c in pack_charades if c["id"] in solved),
        })
    return out


@router.get("/list")
async def list_charades(pack: str | None = None, user: dict = Depends(get_current_user)) -> dict:
    """All charades in a pack (or all packs) + which the user has solved."""
    user_id = str(user["_id"])
    solved = await db.charade_attempts.distinct(
        "charade_id", {"user_id": user_id, "correct": True}
    )
    filtered = charades_for_pack(pack)
    return {
        "charades": [_public_charade(c) for c in filtered],
        "solved_ids": solved,
        "points_per_correct": POINTS_PER_CORRECT,
        "pack": pack or "all",
    }


@router.post("/attempt")
async def attempt_charade(body: AttemptIn, user: dict = Depends(get_current_user)) -> dict:
    """Grade a single attempt. Server-side only — the client never sees the answer.

    Idempotent per (user, charade): re-submitting a correct answer does NOT award
    duplicate points; only the FIRST correct attempt grants XP and counts toward
    the badge. Wrong attempts are logged but don't cost anything.
    """
    charade = next((c for c in CHARADES if c["id"] == body.charade_id), None)
    if not charade:
        raise HTTPException(status_code=404, detail="Charade introuvable")

    user_id = str(user["_id"])
    submitted = normalize(body.answer)
    expected = charade["answer"]
    is_correct = submitted == expected
    now = datetime.now(timezone.utc).isoformat()

    # Have we already awarded this one?
    prior_correct = await db.charade_attempts.find_one(
        {"user_id": user_id, "charade_id": body.charade_id, "correct": True}
    )
    already_solved = prior_correct is not None

    await db.charade_attempts.insert_one({
        "user_id": user_id,
        "charade_id": body.charade_id,
        "answer_submitted": submitted,
        "correct": is_correct,
        "awarded_points": POINTS_PER_CORRECT if (is_correct and not already_solved) else 0,
        "created_at": now,
    })

    points_gained = 0
    awarded_badges: list[dict] = []
    if is_correct and not already_solved:
        points_gained = POINTS_PER_CORRECT
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$inc": {"xp_total": POINTS_PER_CORRECT}},
        )
        # Also credit the weekly league score
        try:
            from routers.gamification import _ensure_league_membership, _week_key
            await _ensure_league_membership(user_id)
            await db.league_scores.update_one(
                {"user_id": user_id, "week_key": _week_key()},
                {"$inc": {"xp": POINTS_PER_CORRECT}, "$setOnInsert": {
                    "user_id": user_id, "week_key": _week_key(),
                    "user_name": user.get("name") or user.get("email", "").split("@")[0],
                }},
                upsert=True,
            )
        except Exception:
            pass

        # Badge: solved N distinct charades correctly
        solved_count = len(await db.charade_attempts.distinct(
            "charade_id", {"user_id": user_id, "correct": True}
        ))
        if solved_count >= BADGE_AT_SOLVED and await award_badge(user_id, "amateur_mots"):
            awarded_badges.append(BADGE_INDEX["amateur_mots"])

    return {
        "correct": is_correct,
        "already_solved": already_solved,
        "expected": charade["answer_display"],  # always reveal the beautiful spelling
        "points_gained": points_gained,
        "awarded_badges": awarded_badges,
    }


@router.get("/progress")
async def my_progress(user: dict = Depends(get_current_user)) -> dict:
    """Personal stats for the Charades game."""
    user_id = str(user["_id"])
    solved = await db.charade_attempts.distinct(
        "charade_id", {"user_id": user_id, "correct": True}
    )
    total_attempts = await db.charade_attempts.count_documents({"user_id": user_id})
    correct_attempts = await db.charade_attempts.count_documents({"user_id": user_id, "correct": True})
    return {
        "total_charades": len(CHARADES),
        "solved_count": len(solved),
        "solved_ids": solved,
        "attempts_total": total_attempts,
        "attempts_correct": correct_attempts,
        "accuracy_pct": round((correct_attempts / total_attempts * 100), 1) if total_attempts else 0.0,
    }
