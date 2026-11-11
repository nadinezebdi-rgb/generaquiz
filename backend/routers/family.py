"""Espace famille : 1 bénéficiaire (abonné Famille/Héritage) + 4 proches invités.

Les proches jouent gratuitement aux quiz et défis du groupe familial et voient
le classement ; le catalogue solo et leur propre Livre de Vie restent payants.
"""
import asyncio
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import resend
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from core import db, logger, FRONTEND_URL, RESEND_API_KEY, SENDER_EMAIL, get_current_user, is_premium_active

router = APIRouter(prefix="/famille", tags=["famille"])

MAX_PROCHES = 4
OWNER_TIERS = {"famille", "famille_v2", "heritage", "premium"}


def is_family_owner(u: dict) -> bool:
    return is_premium_active(u) and u.get("plan_tier") in OWNER_TIERS


async def family_owner_of(u: dict) -> Optional[dict]:
    """Bénéficiaire actif dont `u` est proche (None sinon)."""
    owner_id = u.get("family_owner_id")
    if not owner_id:
        return None
    owner = await db.users.find_one({"_id": ObjectId(owner_id)})
    return owner if owner and is_family_owner(owner) else None


async def has_family_access(u: dict) -> bool:
    return is_family_owner(u) or await family_owner_of(u) is not None


def _invite_public(d: dict) -> dict:
    return {"id": d["id"], "name": d.get("name"), "email": d["email"], "status": d["status"],
            "invited_at": d.get("invited_at"), "accepted_at": d.get("accepted_at"),
            "link": f"{FRONTEND_URL}/famille/rejoindre/{d['token']}"}


async def _send_invite_email(to: str, owner_name: str, link: str) -> None:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY absent — invitation famille non envoyée")
        return
    html = (f"<div style='font-family:Arial,sans-serif;color:#1A2530;max-width:520px'>"
            f"<h2 style='font-family:Georgia,serif;color:#1E3A5F'>{owner_name} vous invite dans sa famille GénéraQuiz</h2>"
            f"<p>Jouez ensemble aux quiz et défis familiaux, toute l'année, gratuitement.</p>"
            f"<p><a href='{link}' style='background:#E07A5F;color:#fff;padding:12px 24px;border-radius:999px;"
            f"text-decoration:none;font-weight:bold'>Rejoindre la famille</a></p></div>")
    try:
        await asyncio.to_thread(resend.Emails.send, {"from": SENDER_EMAIL, "to": [to],
                                "subject": f"{owner_name} vous invite à jouer en famille", "html": html})
    except Exception as e:
        logger.error(f"Invitation famille non envoyée à {to}: {e}")


async def _leaderboard(member_ids: list[str]) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    agg = await db.attempts.aggregate([
        {"$match": {"user_id": {"$in": member_ids}, "created_at": {"$gte": since}}},
        {"$group": {"_id": "$user_id", "games": {"$sum": 1}, "score": {"$sum": "$score"}, "total": {"$sum": "$total"}}},
    ]).to_list(10)
    by_id = {a["_id"]: a for a in agg}
    users = await db.users.find({"_id": {"$in": [ObjectId(i) for i in member_ids]}},
                                {"name": 1, "streak_current": 1}).to_list(10)
    rows = []
    for u in users:
        a = by_id.get(str(u["_id"]), {})
        rows.append({"user_id": str(u["_id"]), "name": u.get("name") or "Un proche",
                     "games": a.get("games", 0), "score": a.get("score", 0),
                     "accuracy": round(100 * a["score"] / a["total"]) if a.get("total") else 0,
                     "streak": int(u.get("streak_current") or 0)})
    return sorted(rows, key=lambda r: (-r["score"], -r["games"]))


async def _space(owner: dict, me: dict, role: str) -> dict:
    owner_id = str(owner["_id"])
    invites = await db.family_proches.find({"owner_id": owner_id, "status": {"$in": ["invited", "accepted"]}},
                                           {"_id": 0}).sort("invited_at", 1).to_list(MAX_PROCHES)
    accepted = [i["user_id"] for i in invites if i["status"] == "accepted" and i.get("user_id")]
    member_ids = [owner_id, *accepted]
    challenges = await db.challenges.find({"creator_user_id": {"$in": member_ids}},
                                          {"_id": 0, "token": 1, "creator_name": 1, "category_title": 1,
                                           "participants": 1, "created_at": 1}).sort("created_at", -1).to_list(10)
    return {
        "role": role, "owner_name": owner.get("name"), "max_proches": MAX_PROCHES,
        "proches": [_invite_public(i) if role == "owner" else {"name": i.get("name"), "status": i["status"]}
                    for i in invites],
        "leaderboard": await _leaderboard(member_ids),
        "challenges": [{"token": c["token"], "creator_name": c["creator_name"],
                        "category_title": c.get("category_title"),
                        "participants": len(c.get("participants", [])), "created_at": c.get("created_at")}
                       for c in challenges],
        "me": str(me["_id"]),
    }


@router.get("")
async def my_family_space(user: dict = Depends(get_current_user)) -> dict:
    if is_family_owner(user):
        return await _space(user, user, "owner")
    owner = await family_owner_of(user)
    if owner:
        return await _space(owner, user, "proche")
    return {"role": "none", "max_proches": MAX_PROCHES}


class ProcheInvite(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)
    email: EmailStr


@router.post("/proches")
async def invite_proche(body: ProcheInvite, user: dict = Depends(get_current_user)) -> dict:
    if not is_family_owner(user):
        raise HTTPException(status_code=402, detail="L'espace famille est inclus dans l'offre Famille")
    owner_id = str(user["_id"])
    email = body.email.lower()
    if email == user["email"].lower():
        raise HTTPException(status_code=400, detail="Vous êtes déjà le bénéficiaire de cet espace")
    active = await db.family_proches.find({"owner_id": owner_id, "status": {"$in": ["invited", "accepted"]}},
                                          {"email": 1}).to_list(MAX_PROCHES + 1)
    if any(a["email"] == email for a in active):
        raise HTTPException(status_code=400, detail="Cette personne est déjà invitée")
    if len(active) >= MAX_PROCHES:
        raise HTTPException(status_code=400, detail=f"Votre espace famille compte déjà {MAX_PROCHES} proches")
    doc = {"id": str(uuid.uuid4()), "owner_id": owner_id, "name": body.name.strip(), "email": email,
           "status": "invited", "token": secrets.token_urlsafe(18), "user_id": None,
           "invited_at": datetime.now(timezone.utc).isoformat(), "accepted_at": None}
    await db.family_proches.insert_one(doc)
    await _send_invite_email(email, user.get("name") or "Un proche", _invite_public(doc)["link"])
    return _invite_public(doc)


@router.delete("/proches/{invite_id}")
async def remove_proche(invite_id: str, user: dict = Depends(get_current_user)) -> dict:
    inv = await db.family_proches.find_one_and_update(
        {"id": invite_id, "owner_id": str(user["_id"]), "status": {"$in": ["invited", "accepted"]}},
        {"$set": {"status": "revoked"}})
    if not inv:
        raise HTTPException(status_code=404, detail="Proche introuvable")
    if inv.get("user_id"):
        await db.users.update_one({"_id": ObjectId(inv["user_id"]), "family_owner_id": str(user["_id"])},
                                  {"$unset": {"family_owner_id": ""}})
    return {"ok": True}


@router.get("/invitation/{token}")
async def invitation_info(token: str) -> dict:
    inv = await db.family_proches.find_one({"token": token, "status": {"$in": ["invited", "accepted"]}})
    if not inv:
        raise HTTPException(status_code=404, detail="Cette invitation n'est plus valable")
    owner = await db.users.find_one({"_id": ObjectId(inv["owner_id"])}, {"name": 1})
    return {"owner_name": (owner or {}).get("name") or "Un proche", "name": inv.get("name"), "status": inv["status"]}


@router.post("/invitation/{token}/accept")
async def accept_invitation(token: str, user: dict = Depends(get_current_user)) -> dict:
    inv = await db.family_proches.find_one({"token": token, "status": {"$in": ["invited", "accepted"]}})
    if not inv:
        raise HTTPException(status_code=404, detail="Cette invitation n'est plus valable")
    uid = str(user["_id"])
    if inv["owner_id"] == uid:
        raise HTTPException(status_code=400, detail="Vous êtes le bénéficiaire de cet espace")
    if inv["status"] == "accepted" and inv.get("user_id") != uid:
        raise HTTPException(status_code=409, detail="Cette invitation a déjà été utilisée")
    if user.get("family_owner_id") and user["family_owner_id"] != inv["owner_id"]:
        raise HTTPException(status_code=409, detail="Vous faites déjà partie d'un autre espace famille")
    await db.family_proches.update_one({"id": inv["id"]}, {"$set": {
        "status": "accepted", "user_id": uid, "accepted_at": datetime.now(timezone.utc).isoformat()}})
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"family_owner_id": inv["owner_id"]}})
    return {"ok": True}


@router.post("/quitter")
async def leave_family(user: dict = Depends(get_current_user)) -> dict:
    owner_id = user.get("family_owner_id")
    if not owner_id:
        raise HTTPException(status_code=400, detail="Vous ne faites partie d'aucun espace famille")
    await db.family_proches.update_many({"owner_id": owner_id, "user_id": str(user["_id"]), "status": "accepted"},
                                        {"$set": {"status": "revoked"}})
    await db.users.update_one({"_id": user["_id"]}, {"$unset": {"family_owner_id": ""}})
    return {"ok": True}
