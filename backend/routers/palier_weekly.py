"""Défi Hebdo Palier — chaque lundi 00:05 Paris, on tire (catégorie, palier)
au sort et on l'affiche pour toute la semaine. Les utilisateurs le jouent via
le parcours normal ; leur meilleur score est tracé dans `weekly_palier_scores`.

Endpoints :
    GET  /api/palier/weekly              : défi de la semaine + top 10
    (le scoring des tentatives est automatique via `record_weekly_score` appelé
     depuis `palier_submit`)

Cron :
    Chaque lundi 00:05 Paris (voir scheduler.py) — `pick_weekly_challenge()`.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from core import db, get_current_user, logger


router = APIRouter(prefix="/palier/weekly", tags=["palier-weekly"])


def _current_iso_week() -> str:
    """Ex: '2026-W08' — clé stable pour toute la semaine (lun→dim)."""
    now = datetime.now(timezone.utc)
    y, w, _ = now.isocalendar()
    return f"{y}-W{w:02d}"


async def pick_weekly_challenge() -> dict:
    """Job cron — tire une (category, palier) au sort et l'enregistre pour la
    semaine ISO courante. Idempotent : si un défi existe déjà pour la semaine,
    on ne le remplace pas."""
    week = _current_iso_week()
    existing = await db.weekly_palier_challenges.find_one({"week": week})
    if existing:
        logger.info(f"[weekly-palier] semaine {week} déjà tirée : {existing.get('category_id')} · palier {existing.get('palier')}")
        return existing

    cats = await db.categories.find({}, {"_id": 0, "id": 1, "title": 1}).to_list(50)
    if not cats:
        logger.warning("[weekly-palier] aucune catégorie disponible")
        return {}
    # On limite aux paliers 2..6 (palier 1 trop facile, palier 7 réservé aux
    # experts). Sélection uniforme.
    cat = random.choice(cats)
    palier = random.randint(2, 6)

    doc = {
        "week": week,
        "category_id": cat["id"],
        "category_title": cat["title"],
        "palier": palier,
        "picked_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.weekly_palier_challenges.insert_one(doc)
    logger.info(f"[weekly-palier] tirage semaine {week} : {cat['title']} · palier {palier}")
    doc.pop("_id", None)
    return doc


async def get_current_challenge() -> Optional[dict]:
    """Retourne le défi courant. Si aucun n'est enregistré (démarrage à froid,
    scheduler en retard), on en tire un immédiatement."""
    week = _current_iso_week()
    doc = await db.weekly_palier_challenges.find_one({"week": week}, {"_id": 0})
    if not doc:
        doc = await pick_weekly_challenge()
        if not doc:
            return None
        doc.pop("_id", None)
    return doc


async def record_weekly_score(user_id: str, category_id: str, palier: int, score: int) -> None:
    """Appelé depuis `palier_submit` — enregistre le meilleur score de la
    semaine si la tentative matche le défi courant."""
    challenge = await get_current_challenge()
    if not challenge:
        return
    if challenge["category_id"] != category_id or challenge["palier"] != palier:
        return
    week = challenge["week"]
    # Upsert best-of : ne baisse jamais le score
    await db.weekly_palier_scores.update_one(
        {"user_id": user_id, "week": week},
        {
            "$max": {"best_score": score},
            "$inc": {"attempts": 1},
            "$set": {
                "user_id": user_id,
                "week": week,
                "category_id": category_id,
                "palier": palier,
                "last_played_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        upsert=True,
    )


@router.get("")
async def weekly_endpoint(user: dict = Depends(get_current_user)) -> dict:
    challenge = await get_current_challenge()
    if not challenge:
        raise HTTPException(status_code=404, detail="Aucun défi actif")
    week = challenge["week"]

    # Enrichit avec le mascot de la catégorie
    cat = await db.categories.find_one({"id": challenge["category_id"]}, {"_id": 0})

    # Leaderboard top 10 de la semaine
    rows = await db.weekly_palier_scores.find(
        {"week": week},
        {"_id": 0, "user_id": 1, "best_score": 1, "attempts": 1, "last_played_at": 1},
    ).sort("best_score", -1).limit(50).to_list(50)

    from bson import ObjectId
    user_ids: list[ObjectId] = []
    for r in rows:
        try: user_ids.append(ObjectId(r["user_id"]))
        except Exception: pass
    users_by_id: dict[str, dict] = {}
    async for u in db.users.find({"_id": {"$in": user_ids}}, {"name": 1, "email": 1}):
        users_by_id[str(u["_id"])] = u

    entries = []
    for rank, row in enumerate(rows[:10], 1):
        u = users_by_id.get(row["user_id"], {})
        entries.append({
            "rank": rank,
            "user_id": row["user_id"],
            "name": u.get("name") or "Anonyme",
            "best_score": row["best_score"],
            "attempts": row.get("attempts", 1),
            "is_current_user": row["user_id"] == str(user["_id"]),
        })

    # Rang du user hors top
    me_row = next(((i, r) for i, r in enumerate(rows, 1) if r["user_id"] == str(user["_id"])), None)
    me_entry = None
    if me_row and me_row[0] > 10:
        i, row = me_row
        me_entry = {
            "rank": i,
            "user_id": row["user_id"],
            "name": user.get("name") or "Vous",
            "best_score": row["best_score"],
            "attempts": row.get("attempts", 1),
            "is_current_user": True,
        }

    return {
        "week": week,
        "category": cat,
        "palier": challenge["palier"],
        "total_players": len(rows),
        "entries": entries,
        "me_out_of_top": me_entry,
    }
