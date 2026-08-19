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
    """Tirage des questions d'un quiz avec deux garde-fous critiques :

    1. Anti-répétition (Correctif A) : les questions vues par l'utilisateur
       dans les 30 derniers jours sont exclues. Si le pool restant est trop
       petit, on complète en repêchant les plus anciennes vues.
    2. Signalements (Correctif C) : les questions ayant reçu au moins 2
       signalements non traités sont exclues automatiquement.

    Les questions renvoyées sont ensuite tracées dans `user_seen_questions`.
    """
    limit = 30 if user.get("plan") == "premium" else 5
    cat = await db.categories.find_one({"id": category_id}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    user_id = str(user["_id"])

    # 1) Questions déjà vues dans les 30 derniers jours
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(days=30)
    seen_docs = await db.user_seen_questions.find(
        {"user_id": user_id, "category_id": category_id, "seen_at": {"$gte": since.isoformat()}},
        {"_id": 0, "question_id": 1},
    ).to_list(2000)
    seen_ids = {d["question_id"] for d in seen_docs}

    # 2) Questions "toxiques" : signalées ≥2 fois avec statut != "dismissed"
    reported = await db.question_reports.aggregate([
        {"$match": {"category_id": category_id, "status": {"$ne": "dismissed"}}},
        {"$group": {"_id": "$question_id", "n": {"$sum": 1}}},
        {"$match": {"n": {"$gte": 2}}},
    ]).to_list(500)
    reported_ids = {r["_id"] for r in reported}

    excluded_ids = seen_ids | reported_ids

    # 3) Premier tirage : questions non-vues, non-signalées, ET non "flagged" par le fact-check
    #    (quality peut être "verified", "flagged", ou absent — on exclut uniquement "flagged")
    base_match = {
        "category_id": category_id,
        "id": {"$nin": list(excluded_ids)},
        "quality": {"$ne": "flagged"},
    }
    pipeline = [
        {"$match": base_match},
        {"$sample": {"size": limit}},
        {"$project": {"_id": 0}},
    ]
    qs = await db.questions.aggregate(pipeline).to_list(limit)

    # 4) Si pas assez de nouvelles questions, on repêche les vues les plus anciennes
    #    (mais on garde le filtre signalements — jamais de question toxique)
    if len(qs) < limit:
        needed = limit - len(qs)
        chosen_ids = {q["id"] for q in qs}
        # Repêche : questions vues (les plus anciennes en priorité), hors signalées et hors flagged
        fallback = await db.questions.aggregate([
            {"$match": {
                "category_id": category_id,
                "id": {"$nin": list(reported_ids | chosen_ids)},
                "quality": {"$ne": "flagged"},
            }},
            {"$sample": {"size": needed}},
            {"$project": {"_id": 0}},
        ]).to_list(needed)
        qs.extend(fallback)

    # 5) Trace les questions montrées à l'utilisateur (upsert pour rafraîchir seen_at)
    if qs:
        now_iso = datetime.now(timezone.utc).isoformat()
        from pymongo import UpdateOne
        await db.user_seen_questions.bulk_write([
            UpdateOne(
                {"user_id": user_id, "question_id": q["id"], "category_id": category_id},
                {"$set": {"seen_at": now_iso, "category_id": category_id}, "$inc": {"seen_count": 1}},
                upsert=True,
            )
            for q in qs
        ], ordered=False)

    # 6) Compteur : X/N questions restantes non vues (basé sur les questions JOUABLES uniquement)
    playable_total = await db.questions.count_documents({
        "category_id": category_id,
        "quality": {"$ne": "flagged"},
        "id": {"$nin": list(reported_ids)} if reported_ids else {"$exists": True},
    })
    # seen_ids peut inclure des questions désormais flagged — on garde le comptage simple :
    seen_playable = await db.questions.count_documents({
        "category_id": category_id,
        "quality": {"$ne": "flagged"},
        "id": {"$in": list(seen_ids)},
    }) if seen_ids else 0
    remaining = max(0, playable_total - seen_playable)

    return {
        "category": cat,
        "questions": qs,
        "is_premium": user.get("plan") == "premium",
        "pool": {
            "total": playable_total,
            "seen_recently": seen_playable,
            "remaining_fresh": remaining,
            "reported_excluded": len(reported_ids),
        },
    }


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
