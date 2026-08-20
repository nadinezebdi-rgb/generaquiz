"""Parcours à paliers — progression utilisateur par difficulté (1..7).

Règles produit :
  - Chaque catégorie propose 7 paliers de 20 questions (140 total).
  - Palier 1 débloqué d'office. Palier N+1 débloqué si score ≥ 14/20 au palier N.
  - En cas d'échec, l'utilisateur rejoue le MÊME set de 20 questions (mêmes
    IDs, on stocke le tirage dans `user_paliers` pour garantir la reprise).
  - Le meilleur score et le nombre de tentatives sont conservés.

Endpoints :
  GET  /api/palier/categories/{category_id}                 → aperçu 7 paliers
  POST /api/palier/categories/{category_id}/{n}/start       → 20 questions
  POST /api/palier/categories/{category_id}/{n}/submit      → scoring + unlock
"""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core import db, get_current_user
from badges import check_after_palier

router = APIRouter(prefix="/palier", tags=["palier"])

TOTAL_PALIERS = 7
PALIER_SIZE = 20
PASS_THRESHOLD = 14  # sur 20


class PalierAnswer(BaseModel):
    question_id: str
    answer_index: int


class PalierSubmit(BaseModel):
    answers: list[PalierAnswer]


PALIER_LABELS = {
    1: "Très facile", 2: "Facile", 3: "Accessible", 4: "Intermédiaire",
    5: "Confirmé", 6: "Difficile", 7: "Expert",
}


async def _get_user_palier(user_id: str, category_id: str, palier: int) -> dict | None:
    return await db.user_paliers.find_one({
        "user_id": user_id, "category_id": category_id, "palier": palier,
    })


@router.get("/categories/{category_id}")
async def palier_overview(category_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Retourne l'état des 7 paliers pour l'utilisateur courant."""
    cat = await db.categories.find_one({"id": category_id}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    user_id = str(user["_id"])
    # Progrès existants
    docs = await db.user_paliers.find(
        {"user_id": user_id, "category_id": category_id},
        {"_id": 0, "palier": 1, "best_score": 1, "completed": 1, "attempts": 1, "last_played_at": 1},
    ).to_list(TOTAL_PALIERS)
    by_palier = {d["palier"]: d for d in docs}

    # Comptage stock disponible par palier (utile pour l'admin QA + hint utilisateur)
    stock_pipeline = [
        {"$match": {"category_id": category_id, "quality": {"$ne": "flagged"},
                    "difficulty": {"$gte": 1, "$lte": 7}}},
        {"$group": {"_id": "$difficulty", "n": {"$sum": 1}}},
    ]
    stock_docs = await db.questions.aggregate(stock_pipeline).to_list(TOTAL_PALIERS)
    stock = {d["_id"]: d["n"] for d in stock_docs}

    paliers = []
    prev_completed = True  # palier 1 toujours débloqué
    for n in range(1, TOTAL_PALIERS + 1):
        prog = by_palier.get(n, {})
        completed = bool(prog.get("completed"))
        unlocked = prev_completed
        paliers.append({
            "palier": n,
            "label": PALIER_LABELS[n],
            "unlocked": unlocked,
            "completed": completed,
            "best_score": prog.get("best_score", 0),
            "attempts": prog.get("attempts", 0),
            "last_played_at": prog.get("last_played_at"),
            "stock_available": stock.get(n, 0),
            "target_size": PALIER_SIZE,
            "pass_threshold": PASS_THRESHOLD,
        })
        prev_completed = completed

    return {
        "category": cat,
        "total_paliers": TOTAL_PALIERS,
        "palier_size": PALIER_SIZE,
        "pass_threshold": PASS_THRESHOLD,
        "paliers": paliers,
    }


@router.post("/categories/{category_id}/{palier}/start")
async def palier_start(category_id: str, palier: int, user: dict = Depends(get_current_user)) -> dict:
    """Renvoie les 20 questions du palier. Sur rejeu, renvoie les MÊMES
    questions (stockées lors du premier tirage) pour permettre de retenter."""
    if palier < 1 or palier > TOTAL_PALIERS:
        raise HTTPException(status_code=400, detail="Palier invalide")

    # Vérifie le déblocage : palier N débloqué si palier N-1 est completed
    user_id = str(user["_id"])
    if palier > 1:
        prev = await _get_user_palier(user_id, category_id, palier - 1)
        if not prev or not prev.get("completed"):
            raise HTTPException(status_code=403, detail=f"Palier {palier - 1} pas encore validé")

    doc = await _get_user_palier(user_id, category_id, palier)
    question_ids = doc.get("question_ids") if doc else None
    completed = bool(doc and doc.get("completed"))

    if question_ids and not completed:
        # Rejeu → mêmes questions
        qs = await db.questions.find(
            {"id": {"$in": question_ids}}, {"_id": 0, "fact_check": 0}
        ).to_list(PALIER_SIZE)
        qs.sort(key=lambda q: question_ids.index(q["id"]))
    else:
        # Premier tirage OU refonte après completion (retenté pour améliorer score)
        pipeline = [
            {"$match": {"category_id": category_id, "difficulty": palier,
                        "quality": {"$ne": "flagged"}}},
            {"$sample": {"size": PALIER_SIZE}},
            {"$project": {"_id": 0, "fact_check": 0}},
        ]
        qs = await db.questions.aggregate(pipeline).to_list(PALIER_SIZE)
        question_ids = [q["id"] for q in qs]
        await db.user_paliers.update_one(
            {"user_id": user_id, "category_id": category_id, "palier": palier},
            {"$set": {
                "user_id": user_id,
                "category_id": category_id,
                "palier": palier,
                "question_ids": question_ids,
                "last_started_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )

    if len(qs) < PALIER_SIZE:
        # Stock insuffisant : on prévient l'utilisateur pour qu'il alerte l'admin
        # (le top-up doit être lancé côté admin).
        raise HTTPException(
            status_code=409,
            detail=f"Stock insuffisant pour ce palier ({len(qs)}/{PALIER_SIZE}). Un admin doit lancer un top-up.",
        )

    return {
        "category_id": category_id,
        "palier": palier,
        "label": PALIER_LABELS[palier],
        "pass_threshold": PASS_THRESHOLD,
        "questions": qs,
    }


@router.post("/categories/{category_id}/{palier}/submit")
async def palier_submit(category_id: str, palier: int, body: PalierSubmit,
                        user: dict = Depends(get_current_user)) -> dict:
    """Server-authoritative scoring — le client ne peut PAS mentir sur son score."""
    if palier < 1 or palier > TOTAL_PALIERS:
        raise HTTPException(status_code=400, detail="Palier invalide")

    user_id = str(user["_id"])
    doc = await _get_user_palier(user_id, category_id, palier)
    expected_ids = (doc or {}).get("question_ids") or []
    if not expected_ids:
        raise HTTPException(status_code=400, detail="Palier non démarré")

    submitted_ids = [a.question_id for a in body.answers]
    if set(submitted_ids) != set(expected_ids):
        raise HTTPException(status_code=400, detail="Les questions ne correspondent pas au palier démarré")

    qs = await db.questions.find(
        {"id": {"$in": expected_ids}},
        {"_id": 0, "id": 1, "correct_index": 1},
    ).to_list(len(expected_ids))
    correct_map = {q["id"]: int(q["correct_index"]) for q in qs}

    score = sum(1 for a in body.answers if correct_map.get(a.question_id) == a.answer_index)
    passed = score >= PASS_THRESHOLD

    prev_best = int((doc or {}).get("best_score", 0))
    prev_completed = bool((doc or {}).get("completed"))
    new_best = max(prev_best, score)
    new_completed = prev_completed or passed
    now_iso = datetime.now(timezone.utc).isoformat()

    update = {
        "best_score": new_best,
        "last_played_at": now_iso,
        "last_score": score,
    }
    if new_completed and not prev_completed:
        update["completed"] = True
        update["completed_at"] = now_iso

    await db.user_paliers.update_one(
        {"user_id": user_id, "category_id": category_id, "palier": palier},
        {"$set": update, "$inc": {"attempts": 1}},
    )

    # Badges palier (expert / grand maître / 20/20 parfait). Idempotent.
    awarded = await check_after_palier(user_id, category_id, palier, score, PALIER_SIZE, passed)

    next_unlocked = new_completed and palier < TOTAL_PALIERS
    return {
        "score": score,
        "total": PALIER_SIZE,
        "passed": passed,
        "best_score": new_best,
        "completed": new_completed,
        "next_palier_unlocked": next_unlocked,
        "next_palier": palier + 1 if next_unlocked else None,
        "awarded_badges": awarded,
    }


@router.get("/leaderboard/{category_id}")
async def palier_leaderboard(category_id: str, limit: int = 10,
                              user: dict = Depends(get_current_user)) -> dict:
    """Top 10 des joueurs d'une catégorie : classement par nombre de paliers
    validés (desc), puis par somme des meilleurs scores (tiebreaker).
    Retourne aussi le rang de l'utilisateur courant s'il n'est pas dans le top."""
    cat = await db.categories.find_one({"id": category_id}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")

    # Agrégation : par user, on compte les paliers completed et somme des best_score
    pipeline = [
        {"$match": {"category_id": category_id, "completed": True}},
        {"$group": {
            "_id": "$user_id",
            "paliers_completed": {"$sum": 1},
            "sum_best": {"$sum": "$best_score"},
            "top_palier": {"$max": "$palier"},
            "last_played_at": {"$max": "$last_played_at"},
        }},
        {"$sort": {"paliers_completed": -1, "sum_best": -1, "last_played_at": 1}},
    ]
    all_rows = await db.user_paliers.aggregate(pipeline).to_list(2000)

    # Enrichit avec nom user + calcule rank
    from bson import ObjectId
    top = all_rows[:limit]
    user_ids = [row["_id"] for row in top]
    users_by_id: dict[str, dict] = {}
    if user_ids:
        oids = []
        for uid in user_ids:
            try: oids.append(ObjectId(uid))
            except Exception: pass
        async for u in db.users.find({"_id": {"$in": oids}}, {"name": 1, "email": 1}):
            users_by_id[str(u["_id"])] = u

    entries = []
    for rank, row in enumerate(top, 1):
        u = users_by_id.get(row["_id"], {})
        entries.append({
            "rank": rank,
            "user_id": row["_id"],
            "name": u.get("name") or "Anonyme",
            "paliers_completed": row["paliers_completed"],
            "sum_best": row["sum_best"],
            "top_palier": row["top_palier"],
            "is_current_user": row["_id"] == str(user["_id"]),
        })

    # Rang de l'utilisateur courant s'il n'est pas dans le top
    me_row = next((i for i, r in enumerate(all_rows, 1) if r["_id"] == str(user["_id"])), None)
    me_entry = None
    if me_row and me_row > limit:
        row = all_rows[me_row - 1]
        me_entry = {
            "rank": me_row,
            "user_id": row["_id"],
            "name": user.get("name") or "Vous",
            "paliers_completed": row["paliers_completed"],
            "sum_best": row["sum_best"],
            "top_palier": row["top_palier"],
            "is_current_user": True,
        }

    return {
        "category": cat,
        "total_players": len(all_rows),
        "entries": entries,
        "me_out_of_top": me_entry,
    }
