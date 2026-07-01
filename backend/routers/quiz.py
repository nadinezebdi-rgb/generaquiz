"""Quiz router: categories, questions, attempts, stats.

Attempts are server-authoritative: the client sends the picked
answer_index per question, the server loads the questions from Mongo
and recomputes the score. Client-declared scores are IGNORED — this
plugs the cheating vector where the browser console could send
`{score:999,total:999}` to auto-win in the leagues.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from core import db, get_current_user, AttemptCreate
from routers.referral import grant_referral_bonus_if_eligible
from progression import record_category_mastery
from badges import check_after_attempt

router = APIRouter(tags=["quiz"])


@router.get("/categories")
async def list_categories():
    return await db.categories.find({}, {"_id": 0}).to_list(100)


@router.get("/categories/{category_id}/questions")
async def get_questions(category_id: str, user: dict = Depends(get_current_user)):
    limit = 30 if user.get("plan") == "premium" else 5
    cat = await db.categories.find_one({"id": category_id}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    qs = await db.questions.aggregate([
        {"$match": {"category_id": category_id}},
        {"$sample": {"size": limit}},
        {"$project": {"_id": 0}},
    ]).to_list(limit)
    return {"category": cat, "questions": qs, "is_premium": user.get("plan") == "premium"}


@router.post("/attempts")
async def save_attempt(body: AttemptCreate, user: dict = Depends(get_current_user)):
    # ---- Server-authoritative scoring -------------------------------------
    question_ids = [a.question_id for a in body.answers]
    docs = await db.questions.find(
        {"id": {"$in": question_ids}, "category_id": body.category_id},
        {"_id": 0, "id": 1, "correct_index": 1},
    ).to_list(len(question_ids))
    correct_map = {d["id"]: int(d["correct_index"]) for d in docs}
    # Every question in the payload must belong to the declared category
    if any(qid not in correct_map for qid in question_ids):
        raise HTTPException(
            status_code=400,
            detail="Une ou plusieurs questions n'appartiennent pas à la catégorie.",
        )
    score = sum(1 for a in body.answers if correct_map.get(a.question_id) == a.answer_index)
    total = len(body.answers)

    await db.attempts.insert_one({
        "user_id": str(user["_id"]), "category_id": body.category_id,
        "score": score, "total": total,
        "duration_seconds": body.duration_seconds,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # ---- Mastery tracking (per user, per category) ------------------------
    mastery = await record_category_mastery(str(user["_id"]), body.category_id, score, total)

    # ---- XP into weekly league cohort + xp_total --------------------------
    xp_gained = 0
    try:
        from core import XP_PER_CORRECT_CATEGORY
        from routers.gamification import _ensure_league_membership, _week_key
        xp_gained = score * XP_PER_CORRECT_CATEGORY
        if xp_gained > 0:
            user_id = str(user["_id"])
            await db.users.update_one({"_id": user["_id"]}, {"$inc": {"xp_total": xp_gained}})
            await _ensure_league_membership(user_id)
            await db.league_scores.update_one(
                {"user_id": user_id, "week_key": _week_key()},
                {"$inc": {"xp": xp_gained}, "$setOnInsert": {
                    "user_id": user_id, "week_key": _week_key(),
                    "user_name": user.get("name") or user.get("email", "").split("@")[0],
                }},
                upsert=True,
            )
    except Exception:
        pass  # XP is best-effort — never break the attempt save

    # ---- Referral bonus + badge checks -----------------------------------
    bonus_granted = await grant_referral_bonus_if_eligible(user)
    fresh_user = await db.users.find_one({"_id": user["_id"]}) or user
    awarded_badges = await check_after_attempt(fresh_user, score, total)

    return {
        "ok": True,
        "score": score,
        "total": total,
        "xp_gained": xp_gained,
        "mastery": mastery,
        "referral_bonus_granted": bonus_granted,
        "awarded_badges": awarded_badges,
    }


@router.get("/attempts")
async def list_attempts(user: dict = Depends(get_current_user)):
    return await db.attempts.find({"user_id": str(user["_id"])}, {"_id": 0}).sort("created_at", -1).to_list(100)


@router.get("/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    user_id = str(user["_id"])
    total = await db.attempts.count_documents({"user_id": user_id})
    agg = await db.attempts.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "score": {"$sum": "$score"}, "total": {"$sum": "$total"}}},
    ]).to_list(1)
    if agg:
        s, t = agg[0]["score"], agg[0]["total"]
        pct = round((s / t) * 100) if t else 0
    else:
        s, t, pct = 0, 0, 0
    return {"quizzes_played": total, "correct_answers": s, "total_answers": t, "accuracy_pct": pct}
