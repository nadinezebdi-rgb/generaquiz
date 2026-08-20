"""Job nocturne — top-up des paliers pour toutes les catégories.

Appelé chaque nuit à 5h00 Paris depuis `scheduler.py`. Génère uniquement les
questions manquantes pour atteindre 20 par difficulté (Mistral/Sonnet + Opus).

Comme le script standalone `topup_paliers.py` est long, on limite le job
nocturne : seulement les paliers qui ont un déficit ≥ 3 questions sont
top-uppés (pour éviter des runs coûteux tous les soirs). Pour un run complet,
l'admin lance manuellement le bouton "Top-up" dans /app/admin/qa.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("quizdantan")

_BACKEND_DIR = Path(__file__).parent
_TOPUP_SCRIPT = _BACKEND_DIR / "topup_paliers.py"
MIN_DEFICIT = 3  # ne top-up que si un palier a ≥ 3 questions manquantes


async def _needs_topup(db) -> list[str]:
    """Retourne la liste des category_ids ayant au moins un palier avec un
    déficit >= MIN_DEFICIT."""
    result: list[str] = []
    cats = await db.categories.find({}, {"_id": 0, "id": 1}).to_list(50)
    for cat in cats:
        pipeline = [
            {"$match": {"category_id": cat["id"], "quality": {"$ne": "flagged"},
                        "difficulty": {"$gte": 1, "$lte": 7}}},
            {"$group": {"_id": "$difficulty", "n": {"$sum": 1}}},
        ]
        by_diff = {d["_id"]: d["n"] async for d in db.questions.aggregate(pipeline)}
        for d in range(1, 8):
            if 20 - by_diff.get(d, 0) >= MIN_DEFICIT:
                result.append(cat["id"])
                break
    return result


async def topup_all_categories_nightly() -> None:
    from core import db  # import local pour éviter le cycle
    cats = await _needs_topup(db)
    if not cats:
        logger.info("[paliers-topup-nightly] rien à faire, toutes les catégories sont complètes")
        return

    logger.info(f"[paliers-topup-nightly] catégories à top-up : {cats}")
    for cat_id in cats:
        env = os.environ.copy()
        env["ONLY_CATEGORY"] = cat_id
        try:
            # subprocess non bloquant, log dans /tmp
            log_path = f"/tmp/paliers_topup_nightly_{cat_id}.log"
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(_TOPUP_SCRIPT),
                cwd=str(_BACKEND_DIR), env=env,
                stdout=open(log_path, "w"),
                stderr=subprocess.STDOUT,
            )
            rc = await proc.wait()
            logger.info(f"[paliers-topup-nightly] {cat_id} rc={rc} log={log_path}")
        except Exception as e:
            logger.warning(f"[paliers-topup-nightly] {cat_id} exception: {e}")
