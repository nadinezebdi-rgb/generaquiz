"""Quiz router: categories, questions, attempts, stats.

Attempts are server-authoritative: the client sends the picked
answer_index per question, the server loads the questions from Mongo
and recomputes the score. Client-declared scores are IGNORED — this
plugs the cheating vector where the browser console could send
`{score:999,total:999}` to auto-win in the leagues.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from core import db, get_current_user, AttemptCreate, is_premium_active
from routers.referral import grant_referral_bonus_if_eligible
from progression import record_category_mastery
from badges import check_after_attempt

router = APIRouter(tags=["quiz"])

FREE_DAILY_QUESTIONS = 5
ISSUED_WINDOW = timedelta(hours=6)
HIDDEN_FIELDS = {"_id": 0, "correct_index": 0, "explanation": 0}  # corrigé côté serveur, via /answer


@router.get("/categories")
async def list_categories():
    cats = await db.categories.find({}, {"_id": 0}).to_list(100)
    counts = {d["_id"]: d["n"] async for d in db.questions.aggregate([
        {"$match": {"quality": {"$ne": "flagged"}}},
        {"$group": {"_id": "$category_id", "n": {"$sum": 1}}},
    ])}
    for c in cats:
        c["count"] = counts.get(c["id"], 0)
    return cats


async def _weekly_pick(category_id: str, weeks_ago: int = 0) -> tuple[list[str], list[str]]:
    """Tirage déterministe de la semaine ISO : [0:6] exemples, [6:9] mini-quiz."""
    import random
    ids = sorted([d["id"] async for d in db.questions.find(
        {"category_id": category_id, "quality": "verified"}, {"_id": 0, "id": 1})])
    year, week, _ = (datetime.now(timezone.utc) - timedelta(weeks=weeks_ago)).isocalendar()
    return ids, random.Random(f"{category_id}-{year}-{week}").sample(ids, min(9, len(ids)))


@router.get("/categories/{category_id}/showcase")
async def category_showcase(category_id: str):
    """Page publique d'un thème : 6 questions vérifiées, renouvelées chaque semaine."""
    cat = await db.categories.find_one({"id": category_id}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    ids, picked = await _weekly_pick(category_id)
    docs = {q["id"]: q async for q in db.questions.find(
        {"id": {"$in": picked}},
        {"_id": 0, "id": 1, "question": 1, "options": 1, "correct_index": 1,
         "explanation": 1, "discussion_prompt": 1, "difficulty": 1},
    )}
    shown = sorted((docs[i] for i in picked[:6] if i in docs), key=lambda q: (q.get("difficulty") or 9, q["id"]))
    samples = [{"question": q["question"], "answer": q["options"][q["correct_index"]],
                "explanation": q.get("explanation", ""), "discussion_prompt": q.get("discussion_prompt")}
               for q in shown]
    # Mini-quiz : 3 autres questions, sans la bonne réponse (vérifiée côté serveur)
    mini = sorted((docs[i] for i in picked[6:9] if i in docs), key=lambda q: q.get("difficulty") or 9)
    mini_quiz = [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in mini]
    others = await db.categories.find(
        {"id": {"$ne": category_id}}, {"_id": 0, "id": 1, "title": 1, "mascot_image": 1, "color": 1}
    ).to_list(50)
    playable = {d["_id"] async for d in db.questions.aggregate([
        {"$match": {"quality": "verified"}}, {"$group": {"_id": "$category_id", "n": {"$sum": 1}}},
        {"$match": {"n": {"$gte": 20}}}])}
    others = [o for o in others if o["id"] in playable]
    return {"category": {**cat, "count": len(ids)}, "samples": samples, "mini_quiz": mini_quiz, "others": others}


class MiniQuizAnswer(BaseModel):
    question_id: str
    choice: int = Field(..., ge=0, le=5)


@router.post("/categories/{category_id}/mini-quiz/answer")
async def mini_quiz_answer(category_id: str, body: MiniQuizAnswer):
    """Correction publique, limitée aux 3 questions du mini-quiz de la semaine
    (ou de la précédente, pour une page ouverte avant lundi)."""
    allowed = set((await _weekly_pick(category_id))[1][6:9]) | set((await _weekly_pick(category_id, 1))[1][6:9])
    if body.question_id not in allowed:
        raise HTTPException(status_code=404, detail="Question introuvable")
    q = await db.questions.find_one(
        {"id": body.question_id, "category_id": category_id, "quality": "verified"},
        {"_id": 0, "correct_index": 1, "explanation": 1},
    )
    if not q:
        raise HTTPException(status_code=404, detail="Question introuvable")
    return {"correct": body.choice == q["correct_index"], "correct_index": q["correct_index"],
            "explanation": q.get("explanation", "")}


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
    cat = await db.categories.find_one({"id": category_id}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    user_id = str(user["_id"])
    limit = 30
    if not is_premium_active(user):
        # Formule Découverte : 5 questions par jour (toutes catégories), pas par appel.
        from zoneinfo import ZoneInfo
        day_start = datetime.now(ZoneInfo("Europe/Paris")).replace(hour=0, minute=0, second=0, microsecond=0)
        limit = max(0, FREE_DAILY_QUESTIONS - await answered_today(user_id))
        if not limit:
            return {"category": cat, "questions": [], "is_premium": False, "daily_limit_reached": True,
                    "pool": None}

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
        {"$project": HIDDEN_FIELDS},
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
            {"$project": HIDDEN_FIELDS},
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

    session_id = str(uuid.uuid4())
    await db.quiz_sessions.insert_one({
        "id": session_id, "user_id": user_id, "category_id": category_id,
        "question_ids": [q["id"] for q in qs], "answers": {}, "answered_count": 0, "consumed": False,
        "created_at": datetime.now(timezone.utc).isoformat()})

    return {
        "category": cat,
        "questions": qs,
        "session_id": session_id,
        "is_premium": is_premium_active(user),
        "pool": {
            "total": playable_total,
            "seen_recently": seen_playable,
            "remaining_fresh": remaining,
            "reported_excluded": len(reported_ids),
        },
    }


class QuizAnswer(BaseModel):
    session_id: str
    question_id: str
    choice: int = Field(ge=0, le=9)


async def answered_today(user_id: str) -> int:
    """Questions réellement répondues aujourd'hui (heure de Paris) — base de la limite Découverte."""
    from zoneinfo import ZoneInfo
    day_start = datetime.now(ZoneInfo("Europe/Paris")).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = await db.quiz_sessions.aggregate([
        {"$match": {"user_id": user_id, "created_at": {"$gte": day_start.astimezone(timezone.utc).isoformat()}}},
        {"$group": {"_id": None, "n": {"$sum": "$answered_count"}}}]).to_list(1)
    return rows[0]["n"] if rows else 0


async def _open_session(session_id: str, user_id: str, category_id: str) -> dict:
    sess = await db.quiz_sessions.find_one({
        "id": session_id, "user_id": user_id, "category_id": category_id, "consumed": False,
        "created_at": {"$gte": (datetime.now(timezone.utc) - ISSUED_WINDOW).isoformat()}})
    if not sess:
        if await db.quiz_sessions.find_one({"id": session_id, "user_id": user_id, "consumed": True}):
            raise HTTPException(status_code=409, detail="Ce score est déjà enregistré.")
        raise HTTPException(status_code=400, detail="Partie expirée : relancez un quiz.")
    return sess


@router.post("/categories/{category_id}/answer")
async def check_answer(category_id: str, body: QuizAnswer, user: dict = Depends(get_current_user)):
    """Correction d'une question de la partie : seul le premier choix compte, et c'est lui qui sera noté."""
    user_id = str(user["_id"])
    sess = await _open_session(body.session_id, user_id, category_id)
    if body.question_id not in sess["question_ids"]:
        raise HTTPException(status_code=404, detail="Question introuvable")
    if body.question_id not in sess["answers"]:
        if not is_premium_active(user) and await answered_today(user_id) >= FREE_DAILY_QUESTIONS:
            raise HTTPException(status_code=403, detail="Vos 5 questions du jour sont jouées. Revenez demain !")
        await db.quiz_sessions.update_one(
            {"id": body.session_id, f"answers.{body.question_id}": {"$exists": False}},
            {"$set": {f"answers.{body.question_id}": body.choice}, "$inc": {"answered_count": 1}})
        sess = await db.quiz_sessions.find_one({"id": body.session_id})
    q = await db.questions.find_one({"id": body.question_id, "category_id": category_id},
                                    {"_id": 0, "correct_index": 1, "explanation": 1})
    if not q:
        raise HTTPException(status_code=404, detail="Question introuvable")
    choice = sess["answers"][body.question_id]
    return {"correct": choice == q["correct_index"], "correct_index": q["correct_index"],
            "explanation": q.get("explanation", "")}


@router.post("/attempts")
async def save_attempt(body: AttemptCreate, user: dict = Depends(get_current_user)):
    # ---- Score calculé sur les réponses enregistrées par /answer, partie utilisable une seule fois ----
    question_ids = [a.question_id for a in body.answers]
    if len(set(question_ids)) != len(question_ids):
        raise HTTPException(status_code=400, detail="Une question ne peut compter qu'une fois.")
    if not body.session_id:
        raise HTTPException(status_code=400, detail="Partie expirée : relancez un quiz pour enregistrer votre score.")
    sess = await _open_session(body.session_id, str(user["_id"]), body.category_id)
    if any(qid not in sess["answers"] for qid in question_ids):
        raise HTTPException(status_code=400, detail="Une ou plusieurs questions n'ont pas été jouées dans cette partie.")
    if not (await db.quiz_sessions.update_one({"id": sess["id"], "consumed": False},
                                              {"$set": {"consumed": True}})).modified_count:
        raise HTTPException(status_code=409, detail="Ce score est déjà enregistré.")
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
    score = sum(1 for qid in question_ids if correct_map.get(qid) == sess["answers"][qid])
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


class MiniClaimAnswer(BaseModel):
    question_id: str
    choice: int = Field(..., ge=0, le=5)


class MiniClaim(BaseModel):
    category_id: str
    answers: list[MiniClaimAnswer] = Field(..., min_length=1, max_length=3)


@router.post("/mini-quiz/claim")
async def claim_mini_quiz(body: MiniClaim, user: dict = Depends(get_current_user)):
    """Rattache au nouveau compte le mini-quiz joué en visiteur. Score recalculé
    côté serveur ; une seule fois par thème et par semaine ; pas d'XP de ligue."""
    week_ids = {}
    for weeks_ago in (0, 1):
        for qid in (await _weekly_pick(body.category_id, weeks_ago))[1][6:9]:
            week_ids.setdefault(qid, weeks_ago)
    qids = [a.question_id for a in body.answers]
    if len(set(qids)) != len(qids) or any(q not in week_ids for q in qids) \
            or len({week_ids[q] for q in qids}) != 1:
        raise HTTPException(status_code=400, detail="Mini-quiz expiré ou invalide")
    year, week, _ = (datetime.now(timezone.utc) - timedelta(weeks=week_ids[qids[0]])).isocalendar()
    mini_week = f"{year}-W{week:02d}"
    user_id = str(user["_id"])
    if await db.attempts.find_one({"user_id": user_id, "source": "mini_quiz",
                                   "category_id": body.category_id, "mini_week": mini_week}):
        return {"ok": True, "already_claimed": True}
    correct_map = {d["id"]: int(d["correct_index"]) async for d in db.questions.find(
        {"id": {"$in": qids}}, {"_id": 0, "id": 1, "correct_index": 1})}
    score = sum(1 for a in body.answers if correct_map.get(a.question_id) == a.choice)
    total = len(body.answers)
    try:
        await db.attempts.insert_one({
            "user_id": user_id, "category_id": body.category_id, "score": score, "total": total,
            "duration_seconds": 0, "source": "mini_quiz", "mini_week": mini_week,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except DuplicateKeyError:
        return {"ok": True, "already_claimed": True}
    await record_category_mastery(user_id, body.category_id, score, total)
    fresh_user = await db.users.find_one({"_id": user["_id"]}) or user
    awarded_badges = await check_after_attempt(fresh_user, score, total)
    return {"ok": True, "already_claimed": False, "score": score, "total": total,
            "awarded_badges": awarded_badges}


@router.get("/attempts")
async def list_attempts(user: dict = Depends(get_current_user)):
    return await db.attempts.find({"user_id": str(user["_id"])}, {"_id": 0}).sort("created_at", -1).to_list(100)


@router.get("/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    user_id = str(user["_id"])
    total, s, t = 0, 0, 0
    for coll in (db.attempts, db.palier_attempts):  # parties classiques + tentatives de palier
        agg = await coll.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "n": {"$sum": 1}, "score": {"$sum": "$score"}, "total": {"$sum": "$total"}}},
        ]).to_list(1)
        if agg:
            total += agg[0]["n"]; s += agg[0]["score"]; t += agg[0]["total"]
    pct = round((s / t) * 100) if t else 0
    return {"quizzes_played": total, "correct_answers": s, "total_answers": t, "accuracy_pct": pct}
