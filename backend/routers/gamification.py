"""Gamification router — credits, leagues, challenge XP, mobile-ready.

Endpoints (all prefixed with /api/gamification by the main app router):
  GET  /credits/balance                — current balance + recent ledger entries
  POST /credits/spend                  — spend N credits with a reason; returns new balance
  POST /credits/earn-ad                — +1 credit per rewarded video, capped 5/day
  POST /challenge/submit               — score a mobile-side challenge attempt (XP + 1 credit)
  GET  /leagues/current                — user's current weekly cohort (30 players) + timer
  POST /streak-saver                   — spend 10 credits to "save" a missed-day streak
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from core import (
    db, logger, get_current_user,
    AD_REWARD_CREDITS, AD_REWARD_DAILY_CAP,
    CHALLENGE_COMPLETE_CREDITS, HINT_5050_COST, STREAK_SAVER_COST,
    XP_PER_CORRECT_DAILY, XP_CHALLENGE_COMPLETION,
    LEAGUES, LEAGUE_COHORT_SIZE, LEAGUE_PROMOTE, LEAGUE_RELEGATE,
)

router = APIRouter(prefix="/gamification", tags=["gamification"])

PARIS_TZ = ZoneInfo("Europe/Paris")

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
ALLOWED_SPEND_REASONS = {"hint_5050", "streak_save", "skip_question", "bonus_question"}


def _now_paris() -> datetime:
    """Returns a timezone-aware datetime in Europe/Paris (handles CET/CEST DST automatically)."""
    return datetime.now(PARIS_TZ)


def _today_key() -> str:
    return _now_paris().strftime("%Y-%m-%d")


def _week_key(when: Optional[datetime] = None) -> str:
    """ISO week, Paris-aware. Format: '2026-W23'."""
    d = when or _now_paris()
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _week_bounds(when: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Monday 00:00 → next Monday 00:00 in Europe/Paris (returned tz-aware)."""
    d = when or _now_paris()
    monday = d - timedelta(days=d.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    next_monday = monday + timedelta(days=7)
    return monday, next_monday


async def _credits_change(user_id: str, delta: int, reason: str) -> int:
    """Atomically apply +/- credits and write an audit ledger entry. Returns the new balance.

    Refuses to go negative (raises 400)."""
    res = await db.users.find_one_and_update(
        {"_id": ObjectId(user_id)} if delta >= 0 else {
            "_id": ObjectId(user_id),
            "credits": {"$gte": -delta},
        },
        {"$inc": {"credits": delta}},
        return_document=ReturnDocument.AFTER,
    )
    if res is None:
        raise HTTPException(status_code=400, detail="Crédits insuffisants")
    new_balance = int(res.get("credits") or 0)
    await db.credit_ledger.insert_one({
        "user_id": user_id,
        "delta": delta,
        "balance_after": new_balance,
        "reason": reason,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return new_balance


def _slugify_name(name: str, fallback: str) -> str:
    s = re.sub(r"\s+", "-", (name or fallback).strip().lower())
    return re.sub(r"[^a-z0-9-]", "", s) or fallback


# ---------------------------------------------------------------------------
# request models
# ---------------------------------------------------------------------------
class SpendRequest(BaseModel):
    amount: int = Field(..., ge=1, le=100)
    reason: str = Field(..., min_length=2, max_length=40)


class AdRewardRequest(BaseModel):
    ad_unit_id: Optional[str] = Field(None, max_length=80)


class ChallengeSubmitRequest(BaseModel):
    category_id: str = Field(..., min_length=2, max_length=80)
    score: int = Field(..., ge=0, le=100)
    total: int = Field(..., ge=1, le=100)
    duration_seconds: int = Field(..., ge=0, le=7200)
    challenge_token: Optional[str] = Field(None, max_length=80)


# ---------------------------------------------------------------------------
# CREDITS
# ---------------------------------------------------------------------------
@router.get("/credits/balance")
async def get_balance(user: dict = Depends(get_current_user)):
    bal = int(user.get("credits") or 0)
    recent = await db.credit_ledger.find(
        {"user_id": str(user["_id"])},
        {"_id": 0},
    ).sort("created_at", -1).to_list(20)
    return {"credits": bal, "recent": recent}


@router.post("/credits/spend")
async def spend_credits(body: SpendRequest, user: dict = Depends(get_current_user)):
    if body.reason not in ALLOWED_SPEND_REASONS:
        raise HTTPException(status_code=400, detail=f"Raison invalide : {body.reason}")
    # Server-side cost validation per reason (anti-cheat)
    if body.reason == "hint_5050" and body.amount != HINT_5050_COST:
        raise HTTPException(status_code=400, detail=f"Indice 50/50 coûte {HINT_5050_COST} crédits")
    if body.reason == "streak_save" and body.amount != STREAK_SAVER_COST:
        raise HTTPException(status_code=400, detail=f"Sauver sa série coûte {STREAK_SAVER_COST} crédits")

    new_balance = await _credits_change(str(user["_id"]), -body.amount, body.reason)
    return {"credits": new_balance, "spent": body.amount, "reason": body.reason}


@router.post("/credits/earn-ad")
async def earn_ad_reward(body: AdRewardRequest, user: dict = Depends(get_current_user)):
    """Grant +1 credit per rewarded video ad. Capped to AD_REWARD_DAILY_CAP per Paris day."""
    today = _today_key()
    count_today = await db.credit_ledger.count_documents({
        "user_id": str(user["_id"]),
        "reason": "ad_reward",
        "created_at": {"$gte": today + "T00:00:00", "$lt": today + "T23:59:59"},
    })
    if count_today >= AD_REWARD_DAILY_CAP:
        raise HTTPException(
            status_code=429,
            detail=f"Limite quotidienne atteinte ({AD_REWARD_DAILY_CAP} pubs par jour).",
        )
    new_balance = await _credits_change(str(user["_id"]), AD_REWARD_CREDITS, "ad_reward")
    return {"credits": new_balance, "earned": AD_REWARD_CREDITS, "remaining_today": AD_REWARD_DAILY_CAP - count_today - 1}


@router.post("/streak-saver")
async def streak_saver(user: dict = Depends(get_current_user)):
    """Spend STREAK_SAVER_COST credits to bump streak_last_date to yesterday.
    Only valid if the user broke their streak between 1 and 2 days ago (not earlier)."""
    if int(user.get("streak_current") or 0) < 2:
        raise HTTPException(status_code=400, detail="Aucune série à sauver — votre série est < 2 jours.")
    last_date = user.get("streak_last_date")
    yesterday = (_now_paris() - timedelta(days=1)).strftime("%Y-%m-%d")
    day_before = (_now_paris() - timedelta(days=2)).strftime("%Y-%m-%d")
    if last_date not in (day_before,):
        raise HTTPException(
            status_code=400,
            detail="Sauvetage uniquement disponible si vous avez raté UN seul jour.",
        )
    new_balance = await _credits_change(str(user["_id"]), -STREAK_SAVER_COST, "streak_save")
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"streak_last_date": yesterday}},
    )
    return {"credits": new_balance, "streak_last_date": yesterday}


# ---------------------------------------------------------------------------
# CHALLENGE (mobile-side scoring)
# ---------------------------------------------------------------------------
@router.post("/challenge/submit")
async def submit_challenge(body: ChallengeSubmitRequest, user: dict = Depends(get_current_user)):
    """Mobile-friendly challenge submission: persists score, awards XP + 1 credit."""
    user_id = str(user["_id"])
    # Persist attempt for stats
    doc = {
        "user_id": user_id,
        "category_id": body.category_id,
        "score": body.score,
        "total": body.total,
        "duration_seconds": body.duration_seconds,
        "challenge_token": body.challenge_token,
        "source": "mobile_challenge",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.attempts.insert_one(doc)

    # Award XP and 1 credit
    xp_gained = XP_CHALLENGE_COMPLETION + body.score  # base + bonus per correct
    week_key = _week_key()
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$inc": {"xp_total": xp_gained}},
    )
    await _credits_change(user_id, CHALLENGE_COMPLETE_CREDITS, "challenge_complete")
    # Add weekly XP to league cohort (lazy enrollment if needed)
    await _ensure_league_membership(user_id)
    await db.league_scores.update_one(
        {"user_id": user_id, "week_key": week_key},
        {"$inc": {"xp": xp_gained}, "$setOnInsert": {
            "user_id": user_id, "week_key": week_key,
            "user_name": user.get("name") or user["email"].split("@")[0],
        }},
        upsert=True,
    )

    return {
        "ok": True,
        "xp_gained": xp_gained,
        "xp_total": int(user.get("xp_total") or 0) + xp_gained,
        "credits_gained": CHALLENGE_COMPLETE_CREDITS,
    }


# ---------------------------------------------------------------------------
# LEAGUES
# ---------------------------------------------------------------------------
async def _ensure_league_membership(user_id: str) -> dict:
    """Make sure the user has a current-week membership doc, with a deterministic cohort."""
    week_key = _week_key()
    existing = await db.league_memberships.find_one({"user_id": user_id, "week_key": week_key})
    if existing:
        return existing

    # New week: keep the user's previous league tier (from any previous membership), default bronze.
    prev = await db.league_memberships.find(
        {"user_id": user_id},
    ).sort("week_key", -1).limit(1).to_list(1)
    tier = (prev[0]["tier"] if prev else "bronze")
    if tier not in LEAGUES:
        tier = "bronze"

    # Cohort assignment: hash(user_id + week_key + tier) % bucket_count → bucket.
    # Bucket count is tuned to keep cohorts populated even at low DAU.
    # With 10 000 buckets, low-traffic users sit alone (bad UX). At ~30 users
    # per active tier we want ≤ 10 buckets so cohorts of 3-10 form quickly.
    # We start with `LEAGUE_BUCKETS_PER_TIER=10`; once DAU exceeds 300, lift it.
    LEAGUE_BUCKETS_PER_TIER = 10
    bucket = int(hashlib.sha256(f"{user_id}|{week_key}|{tier}".encode()).hexdigest()[:8], 16)
    cohort_id = f"{week_key}-{tier}-{bucket % LEAGUE_BUCKETS_PER_TIER:02d}"

    doc = {
        "user_id": user_id,
        "week_key": week_key,
        "tier": tier,
        "cohort_id": cohort_id,
        "joined_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.league_memberships.insert_one(doc)
    return doc


@router.get("/leagues/current")
async def league_current(user: dict = Depends(get_current_user)):
    user_id = str(user["_id"])
    membership = await _ensure_league_membership(user_id)
    week_key = membership["week_key"]
    cohort_id = membership["cohort_id"]
    tier = membership["tier"]

    # All members of this cohort + their weekly XP
    cohort_members = await db.league_memberships.find(
        {"cohort_id": cohort_id, "week_key": week_key},
        {"_id": 0, "user_id": 1},
    ).to_list(LEAGUE_COHORT_SIZE * 2)
    user_ids = [m["user_id"] for m in cohort_members]

    scores_map: dict[str, int] = {}
    async for s in db.league_scores.find({"user_id": {"$in": user_ids}, "week_key": week_key}):
        scores_map[s["user_id"]] = int(s.get("xp", 0))

    # Build leaderboard
    leaderboard = []
    for uid in user_ids:
        u = await db.users.find_one({"_id": ObjectId(uid)}, {"name": 1, "email": 1, "_id": 0})
        display_name = (u or {}).get("name") or (u or {}).get("email", "?").split("@")[0]
        leaderboard.append({
            "user_id": uid,
            "name": display_name,
            "xp": scores_map.get(uid, 0),
            "is_me": uid == user_id,
        })
    leaderboard.sort(key=lambda r: (-r["xp"], r["name"].lower()))
    for i, row in enumerate(leaderboard, start=1):
        row["rank"] = i

    week_start, week_end = _week_bounds()
    now = _now_paris()
    seconds_left = max(0, int((week_end - now).total_seconds()))

    my_row = next((r for r in leaderboard if r["is_me"]), None)
    tier_index = LEAGUES.index(tier)
    return {
        "tier": tier,
        "tier_label": tier.capitalize(),
        "tier_index": tier_index,
        "next_tier": LEAGUES[tier_index + 1] if tier_index + 1 < len(LEAGUES) else None,
        "previous_tier": LEAGUES[tier_index - 1] if tier_index > 0 else None,
        "cohort_id": cohort_id,
        "week_key": week_key,
        "week_ends_at": week_end.isoformat(),
        "seconds_until_close": seconds_left,
        "promote_top": LEAGUE_PROMOTE,
        "relegate_bottom": LEAGUE_RELEGATE,
        "cohort_size": len(leaderboard),
        "max_cohort_size": LEAGUE_COHORT_SIZE,
        "my_rank": my_row["rank"] if my_row else None,
        "my_xp": my_row["xp"] if my_row else 0,
        "leaderboard": leaderboard,
    }


async def settle_finished_week(when: Optional[datetime] = None) -> dict:
    """Close out the *previous* week: promote top 5 and relegate bottom 3 in every cohort.

    Called by a scheduled job at Monday 00:05 Europe/Paris.
    """
    # Resolve previous week key
    ref = (when or _now_paris()) - timedelta(days=7)
    prev_week = _week_key(ref)

    cohorts = await db.league_memberships.distinct("cohort_id", {"week_key": prev_week})
    promoted = relegated = 0

    for cohort_id in cohorts:
        members = await db.league_memberships.find(
            {"cohort_id": cohort_id, "week_key": prev_week},
        ).to_list(LEAGUE_COHORT_SIZE * 2)
        if not members:
            continue
        # Fetch their XP
        user_ids = [m["user_id"] for m in members]
        scores_map: dict[str, int] = {}
        async for s in db.league_scores.find({"user_id": {"$in": user_ids}, "week_key": prev_week}):
            scores_map[s["user_id"]] = int(s.get("xp", 0))
        ranked = sorted(members, key=lambda m: scores_map.get(m["user_id"], 0), reverse=True)

        for idx, m in enumerate(ranked):
            tier = m["tier"]
            tier_idx = LEAGUES.index(tier) if tier in LEAGUES else 0
            new_tier = tier
            if idx < LEAGUE_PROMOTE and tier_idx + 1 < len(LEAGUES):
                new_tier = LEAGUES[tier_idx + 1]
                promoted += 1
            elif idx >= len(ranked) - LEAGUE_RELEGATE and tier_idx - 1 >= 0:
                new_tier = LEAGUES[tier_idx - 1]
                relegated += 1
            # Record final settlement for that previous week (audit trail)
            await db.league_memberships.update_one(
                {"_id": m["_id"]},
                {"$set": {"final_rank": idx + 1, "settled_to_tier": new_tier}},
            )
            # Badge check for promotions / diamond tier (best-effort)
            if new_tier != tier:
                try:
                    from badges import check_after_league_settle
                    await check_after_league_settle(
                        m["user_id"],
                        new_tier,
                        promoted=(idx < LEAGUE_PROMOTE),
                    )
                except Exception:
                    pass
            # Seed next week's membership in the new tier (lazy: actual cohort assignment on first play)
            # We just remember the tier; cohort will be (re)hashed on next call to _ensure_league_membership.

    logger.info(f"[leagues] settled week={prev_week}: promoted={promoted}, relegated={relegated}, cohorts={len(cohorts)}")
    return {"week": prev_week, "promoted": promoted, "relegated": relegated, "cohorts": len(cohorts)}
