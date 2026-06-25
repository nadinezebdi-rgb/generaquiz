"""Referral router — per-user invite code + bonus on first sponsored attempt.

Mechanics (P2 spec):
  - Each user has a unique referral_code (assigned at register / backfilled).
  - During signup, an optional `referral_code` field can be provided.
  - When the referred user completes their FIRST quiz attempt, BOTH the referrer
    and the referred user receive +5 credits (REFERRAL_BONUS_CREDITS) and a
    `referral_bonus_granted=True` flag is set on the referred user to make the
    bonus idempotent.

Endpoints:
  GET  /api/referral/my            — current user's code + invite stats
  POST /api/referral/validate-code — public (not auth'd): verify a code at register time
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, get_current_user, FRONTEND_URL, REFERRAL_BONUS_CREDITS

router = APIRouter(prefix="/referral", tags=["referral"])

CODE_SUFFIX_LEN = 4
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I confusion
CODE_REGEX = re.compile(r"^[A-Z0-9-]{4,40}$")


def _normalize(code: str) -> str:
    return (code or "").strip().upper()


def _slug_prefix(name: str, email: str) -> str:
    """Take the user's first name (or email local part), uppercase, max 8 chars,
    keeping only A-Z."""
    raw = (name or email.split("@")[0] or "USER").upper()
    cleaned = re.sub(r"[^A-Z]", "", raw)[:8] or "USER"
    return cleaned


async def _is_code_taken(code: str) -> bool:
    return await db.users.find_one({"referral_code": code}, {"_id": 1}) is not None


async def generate_referral_code_for(name: str, email: str) -> str:
    """Produce a unique code like 'MARIE-X7K2'. Retries on rare collisions."""
    prefix = _slug_prefix(name, email)
    for _ in range(8):
        suffix = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_SUFFIX_LEN))
        candidate = f"{prefix}-{suffix}"
        if not await _is_code_taken(candidate):
            return candidate
    # extremely unlikely: extend suffix length
    suffix = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_SUFFIX_LEN + 2))
    return f"{prefix}-{suffix}"


async def find_user_by_code(code: str) -> dict | None:
    norm = _normalize(code)
    if not norm or not CODE_REGEX.match(norm):
        return None
    return await db.users.find_one({"referral_code": norm})


async def grant_referral_bonus_if_eligible(user: dict) -> bool:
    """Called after a successful quiz attempt. If the user has a referrer and
    hasn't received the bonus yet, credit both sides +REFERRAL_BONUS_CREDITS.

    Returns True if the bonus was granted in this call.
    """
    if user.get("referral_bonus_granted"):
        return False
    referrer_id = user.get("referred_by_user_id")
    if not referrer_id:
        return False

    # Atomic-ish: flip the flag first to avoid double crediting if 2 attempts
    # land within the same millisecond.
    res = await db.users.update_one(
        {"_id": user["_id"], "referral_bonus_granted": {"$ne": True}},
        {"$set": {"referral_bonus_granted": True,
                  "referral_bonus_granted_at": datetime.now(timezone.utc).isoformat()},
         "$inc": {"credits": REFERRAL_BONUS_CREDITS}},
    )
    if res.modified_count == 0:
        return False  # someone else won the race

    # Credit the referrer + audit ledger entries for both
    await db.users.update_one(
        {"_id": ObjectId(referrer_id)},
        {"$inc": {"credits": REFERRAL_BONUS_CREDITS,
                  "referral_count": 1}},
    )
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.credit_ledger.insert_many([
        {"user_id": str(user["_id"]), "delta": REFERRAL_BONUS_CREDITS,
         "reason": "referral_bonus_referred", "created_at": now_iso,
         "balance_after": None},
        {"user_id": referrer_id, "delta": REFERRAL_BONUS_CREDITS,
         "reason": "referral_bonus_referrer", "created_at": now_iso,
         "balance_after": None,
         "meta": {"referred_user_id": str(user["_id"])}},
    ])
    return True


class ValidateCodeRequest(BaseModel):
    code: str = Field(min_length=4, max_length=40)


@router.post("/validate-code")
async def validate_code(body: ValidateCodeRequest) -> dict:
    """Public endpoint used by the signup form to live-check a referral code."""
    norm = _normalize(body.code)
    if not CODE_REGEX.match(norm):
        return {"valid": False, "reason": "format"}
    owner = await find_user_by_code(norm)
    if not owner:
        return {"valid": False, "reason": "unknown"}
    # Reveal only the first name to avoid leaking email
    sponsor_name = (owner.get("name") or owner.get("email", "").split("@")[0]).split(" ")[0]
    return {"valid": True, "sponsor_name": sponsor_name, "bonus": REFERRAL_BONUS_CREDITS}


@router.get("/my")
async def my_referral(user: dict = Depends(get_current_user)) -> dict:
    """Return the current user's referral code, count of successful referrals,
    and a ready-to-share invite link."""
    code = user.get("referral_code")
    if not code:
        # Backfill on first call (idempotent — handles users created before P2)
        code = await generate_referral_code_for(user.get("name", ""), user.get("email", ""))
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"referral_code": code}},
        )
    return {
        "code": code,
        "invite_link": f"{FRONTEND_URL}/register?code={code}",
        "referral_count": int(user.get("referral_count") or 0),
        "bonus": REFERRAL_BONUS_CREDITS,
    }
