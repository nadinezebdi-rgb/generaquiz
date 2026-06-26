"""Cooperative Challenges router — "Défi Famille Coopératif" (same device MVP).

Concept:
  Two players take turns on the SAME phone. The creator assigns each
  player a name and a role ("senior" or "jeune"). Questions alternate
  between the two players. If a player is stuck, they tap "Demander
  de l'aide" which physically hands the phone to the partner who tries
  to answer the SAME question. Scoring:
    - Correct alone:        100 XP
    - Correct with help:     50 XP
    - Wrong:                  0 XP

  No real-time sync needed (single device), no Premium gate for now
  (we want to drive engagement first).
"""
from __future__ import annotations

import random
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, conlist

from core import db, get_current_user

router = APIRouter(prefix="/coop-challenges", tags=["coop-challenges"])

XP_SOLO_CORRECT = 100
XP_HELP_CORRECT = 50
XP_WRONG = 0
DEFAULT_NUM_QUESTIONS = 10


# ---- Pydantic models -----------------------------------------------------

class CoopPlayer(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    role: str = Field(pattern="^(senior|jeune)$")


class CoopChallengeCreate(BaseModel):
    team_name: str = Field(min_length=1, max_length=40)
    category_id: str
    players: conlist(CoopPlayer, min_length=2, max_length=2)
    num_questions: int = Field(DEFAULT_NUM_QUESTIONS, ge=4, le=20)


class CoopAnswerRequest(BaseModel):
    answer_index: int = Field(ge=0, le=3)
    help_used: bool = False


# ---- Helpers -------------------------------------------------------------

def _public_view(doc: dict, current_question: Optional[dict] = None) -> dict:
    """Strip private fields (correct_index, explanation) before returning."""
    questions_safe = []
    for q in doc.get("questions", []):
        questions_safe.append({
            "id": q["id"],
            "question": q["question"],
            "options": q["options"],
            "assigned_to": q.get("assigned_to"),  # "senior" | "jeune"
        })
    return {
        "token": doc["token"],
        "team_name": doc["team_name"],
        "category_id": doc["category_id"],
        "category_title": doc.get("category_title"),
        "players": doc["players"],
        "questions": questions_safe,
        "total": len(questions_safe),
        "current_index": doc.get("current_index", 0),
        "stats_coop": doc.get("stats_coop", {}),
        "status": doc.get("status", "in_progress"),
        "answers_log": doc.get("answers_log", []),
        "created_at": doc.get("created_at"),
        "completed_at": doc.get("completed_at"),
    }


def _assign_role(player1_role: str, player2_role: str, idx: int) -> str:
    """Alternate questions: even → player1, odd → player2.

    Returns the role of the player whose turn it is at question `idx`.
    """
    return player1_role if idx % 2 == 0 else player2_role


# ---- Endpoints -----------------------------------------------------------

@router.post("")
async def create_coop_challenge(
    body: CoopChallengeCreate,
    user: dict = Depends(get_current_user),
):
    """Create a new cooperative challenge. Both players must have DIFFERENT
    roles (one senior + one jeune) — same role on both sides would defeat
    the asymmetric design. We tolerate identical roles only with an explicit
    warning in the response."""
    if body.players[0].role == body.players[1].role:
        raise HTTPException(
            status_code=400,
            detail="Les deux joueurs doivent avoir des rôles différents (un Senior + un Jeune)",
        )

    cat = await db.categories.find_one({"id": body.category_id}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    pool = await db.questions.find(
        {"category_id": body.category_id}, {"_id": 0}
    ).to_list(500)
    if len(pool) < body.num_questions:
        raise HTTPException(
            status_code=400,
            detail=f"Pas assez de questions dans cette catégorie (requis: {body.num_questions})",
        )
    random.shuffle(pool)
    selected = pool[: body.num_questions]

    # Annotate each question with the role of the player whose turn it is
    p1_role = body.players[0].role
    p2_role = body.players[1].role
    for idx, q in enumerate(selected):
        q["assigned_to"] = _assign_role(p1_role, p2_role, idx)

    token = secrets.token_urlsafe(8)
    doc = {
        "token": token,
        "creator_user_id": str(user["_id"]),
        "team_name": body.team_name.strip(),
        "category_id": body.category_id,
        "category_title": cat["title"],
        "category_mascot_image": cat.get("mascot_image"),
        "players": [p.model_dump() for p in body.players],
        "questions": selected,
        "current_index": 0,
        "answers_log": [],
        "stats_coop": {
            "total_score": 0,
            "total_xp": 0,
            "helps_used": 0,
            "helps_successful": 0,
            "correct_count": 0,
        },
        "status": "in_progress",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }
    await db.coop_challenges.insert_one(doc)
    return {"token": token, "total": len(selected), "team_name": doc["team_name"]}


@router.get("/{token}")
async def get_coop_challenge(token: str, user: dict = Depends(get_current_user)):
    doc = await db.coop_challenges.find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Défi coopératif introuvable")
    if doc["creator_user_id"] != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Vous n'êtes pas l'organisateur de ce défi")
    return _public_view(doc)


@router.post("/{token}/answer")
async def answer_coop_question(
    token: str,
    body: CoopAnswerRequest,
    user: dict = Depends(get_current_user),
):
    """Submit an answer for the current question and advance the cursor.

    `help_used=true` means the partner answered (we credit only XP_HELP_CORRECT
    if the answer is correct). The flag is set client-side after the user taps
    "Demander de l'aide" and the partner answers on the same device.
    """
    doc = await db.coop_challenges.find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Défi coopératif introuvable")
    if doc["creator_user_id"] != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Vous n'êtes pas l'organisateur de ce défi")
    if doc.get("status") == "completed":
        raise HTTPException(status_code=400, detail="Ce défi est déjà terminé")

    idx = doc.get("current_index", 0)
    questions = doc.get("questions", [])
    if idx >= len(questions):
        raise HTTPException(status_code=400, detail="Toutes les questions ont été répondues")

    q = questions[idx]
    is_correct = body.answer_index == q["correct_index"]
    xp_earned = (
        XP_HELP_CORRECT if (is_correct and body.help_used)
        else XP_SOLO_CORRECT if is_correct
        else XP_WRONG
    )

    # Build the log entry — we keep the question text + correct answer so the
    # final results screen can show the explanation per question.
    log_entry = {
        "index": idx,
        "question_id": q["id"],
        "question": q["question"],
        "options": q["options"],
        "correct_index": q["correct_index"],
        "chosen_index": body.answer_index,
        "is_correct": is_correct,
        "help_used": body.help_used,
        "xp_earned": xp_earned,
        "assigned_to": q.get("assigned_to"),
        "explanation": q.get("explanation", ""),
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }

    new_idx = idx + 1
    completed = new_idx >= len(questions)

    # Conditional update guards against double-tap races: if the cursor has
    # already moved (another in-flight POST won the race), we abort to avoid
    # double-incrementing stats_coop / writing two log rows for the same Q.
    set_fields = {"current_index": new_idx}
    if completed:
        set_fields["status"] = "completed"
        set_fields["completed_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.coop_challenges.update_one(
        {"token": token, "current_index": idx, "status": "in_progress"},
        {
            "$set": set_fields,
            "$push": {"answers_log": log_entry},
            "$inc": {
                "stats_coop.total_xp": xp_earned,
                "stats_coop.correct_count": 1 if is_correct else 0,
                "stats_coop.helps_used": 1 if body.help_used else 0,
                "stats_coop.helps_successful": 1 if (body.help_used and is_correct) else 0,
                "stats_coop.total_score": 1 if is_correct else 0,
            },
        },
    )
    if res.modified_count == 0:
        raise HTTPException(
            status_code=409,
            detail="Cette question a déjà été répondue (double-tap ?). Rechargez la page.",
        )

    # Feed the user's XP (from coop scoring) into both their total and the
    # weekly league cohort — gives Sprint 1 leagues page real data and rewards
    # the cooperative gameplay equally to solo play.
    if xp_earned > 0:
        try:
            from routers.gamification import _ensure_league_membership, _week_key
            user_id = str(user["_id"])
            await db.users.update_one({"_id": user["_id"]}, {"$inc": {"xp_total": xp_earned}})
            await _ensure_league_membership(user_id)
            await db.league_scores.update_one(
                {"user_id": user_id, "week_key": _week_key()},
                {"$inc": {"xp": xp_earned}, "$setOnInsert": {
                    "user_id": user_id, "week_key": _week_key(),
                    "user_name": user.get("name") or user.get("email", "").split("@")[0],
                }},
                upsert=True,
            )
        except Exception:
            # XP attribution is best-effort — never fail the answer endpoint
            pass

    # Reload to return the freshest state to the client
    fresh = await db.coop_challenges.find_one({"token": token})
    next_q = None
    if not completed and new_idx < len(questions):
        nq = questions[new_idx]
        next_q = {
            "id": nq["id"],
            "question": nq["question"],
            "options": nq["options"],
            "assigned_to": nq.get("assigned_to"),
            "index": new_idx,
        }
    return {
        "is_correct": is_correct,
        "correct_index": q["correct_index"],
        "explanation": q.get("explanation", ""),
        "xp_earned": xp_earned,
        "help_used": body.help_used,
        "completed": completed,
        "stats_coop": fresh["stats_coop"],
        "next_question": next_q,
        "total": len(questions),
    }


@router.get("/mine/list")
async def list_my_coop_challenges(user: dict = Depends(get_current_user)):
    """List the current user's cooperative challenges (most recent first)."""
    rows = await db.coop_challenges.find(
        {"creator_user_id": str(user["_id"])},
        # Hide answer keys from the bulk list — clients only need summary
        {"_id": 0, "questions.correct_index": 0, "questions.explanation": 0,
         "answers_log.correct_index": 0, "answers_log.explanation": 0},
    ).sort("created_at", -1).to_list(50)
    for r in rows:
        r["total_questions"] = len(r.get("questions", []))
    return rows
