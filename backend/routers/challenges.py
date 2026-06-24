"""Challenges router: Défi Famille — public + creator-only endpoints."""
import random
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from core import db, get_current_user, ChallengeCreate, ChallengeParticipate

router = APIRouter(prefix="/challenges", tags=["challenges"])


def _public_challenge(doc: dict, include_correct: bool = False) -> dict:
    qs = []
    for q in doc.get("questions", []):
        item = {"id": q["id"], "question": q["question"], "options": q["options"]}
        if include_correct:
            item["correct_index"] = q["correct_index"]
            item["explanation"] = q.get("explanation", "")
        qs.append(item)
    return {"token": doc["token"], "category_id": doc["category_id"],
            "creator_name": doc["creator_name"], "questions": qs, "total": len(qs),
            "participants": sorted(doc.get("participants", []),
                                    key=lambda p: (-p.get("score", 0), p.get("duration_seconds") or 9999)),
            "created_at": doc.get("created_at")}


@router.post("")
async def create_challenge(body: ChallengeCreate, user: dict = Depends(get_current_user)):
    if user.get("plan") != "premium":
        raise HTTPException(status_code=402, detail="Le Défi Famille est réservé aux membres Premium")
    cat = await db.categories.find_one({"id": body.category_id}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    pool = await db.questions.find({"category_id": body.category_id}, {"_id": 0}).to_list(200)
    if len(pool) < 3:
        raise HTTPException(status_code=400, detail="Pas assez de questions dans cette catégorie")
    random.shuffle(pool)
    selected = pool[: min(body.num_questions, len(pool))]
    token = secrets.token_urlsafe(8)
    doc = {"token": token, "creator_user_id": str(user["_id"]),
           "creator_name": user.get("name", "Un proche"), "category_id": body.category_id,
           "category_title": cat["title"], "category_mascot_image": cat.get("mascot_image"),
           "category_mascot_name": cat.get("mascot_name"), "questions": selected,
           "participants": [], "created_at": datetime.now(timezone.utc).isoformat()}
    await db.challenges.insert_one(doc)
    return {"token": token, "total": len(selected), "category": cat}


@router.get("/mine")
async def list_my_challenges(user: dict = Depends(get_current_user)):
    rows = await db.challenges.find({"creator_user_id": str(user["_id"])},
                                     {"_id": 0, "questions.correct_index": 0, "questions.explanation": 0}
                                     ).sort("created_at", -1).to_list(50)
    for r in rows:
        r["participants"] = sorted(r.get("participants", []),
                                    key=lambda p: (-p.get("score", 0), p.get("duration_seconds") or 9999))
        r["total_questions"] = len(r.get("questions", []))
    return rows


@router.get("/{token}")
async def get_challenge(token: str):
    doc = await db.challenges.find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Défi introuvable")
    return {**_public_challenge(doc, include_correct=False),
            "category_title": doc.get("category_title"),
            "category_mascot_image": doc.get("category_mascot_image"),
            "category_mascot_name": doc.get("category_mascot_name")}


@router.post("/{token}/participate")
async def participate_challenge(token: str, body: ChallengeParticipate):
    doc = await db.challenges.find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Défi introuvable")
    qs = doc.get("questions", [])
    if len(body.answers) != len(qs):
        raise HTTPException(status_code=400, detail="Nombre de réponses invalide")
    score = 0
    detail = []
    for i, q in enumerate(qs):
        chosen = body.answers[i]
        is_correct = chosen == q["correct_index"]
        if is_correct:
            score += 1
        detail.append({"question_id": q["id"], "chosen": chosen, "correct_index": q["correct_index"],
                       "is_correct": is_correct, "explanation": q.get("explanation", "")})
    participant = {"name": body.name.strip()[:40], "score": score, "total": len(qs),
                   "duration_seconds": body.duration_seconds,
                   "completed_at": datetime.now(timezone.utc).isoformat()}
    await db.challenges.update_one({"token": token}, {"$push": {"participants": participant}})
    fresh = await db.challenges.find_one({"token": token})
    leaderboard = sorted(fresh.get("participants", []),
                          key=lambda p: (-p.get("score", 0), p.get("duration_seconds") or 9999))
    return {"score": score, "total": len(qs), "detail": detail, "leaderboard": leaderboard}
