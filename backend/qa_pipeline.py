"""Briques partagées du pipeline QA : RETAG sans IA + checkpoints de job (A3)."""
from __future__ import annotations

import os
import time

TARGET_PER_PALIER = 20
PALIERS = range(1, 8)
UNTAGGED_OR = [
    {"difficulty": {"$exists": False}},
    {"difficulty": None},
    {"difficulty": {"$lt": 1}},
    {"difficulty": {"$gt": 7}},
]


async def palier_distribution(db, category_id: str) -> dict[int, int]:
    """Questions jouables (quality != flagged) par palier 1..7."""
    dist = {p: 0 for p in PALIERS}
    async for d in db.questions.aggregate([
        {"$match": {"category_id": category_id, "quality": {"$ne": "flagged"},
                    "difficulty": {"$gte": 1, "$lte": 7}}},
        {"$group": {"_id": "$difficulty", "n": {"$sum": 1}}},
    ]):
        dist[d["_id"]] = d["n"]
    return dist


def pick_palier(dist: dict[int, int], target: int = TARGET_PER_PALIER) -> int | None:
    """Palier le plus vide (préférence palier haut à égalité), None si tout est plein."""
    best = min(PALIERS, key=lambda p: (dist[p], -p))
    return None if dist[best] >= target else best


def missing_slots(dist: dict[int, int], target: int = TARGET_PER_PALIER) -> int:
    return sum(max(0, target - dist[p]) for p in PALIERS)


async def retag_untagged(db, category_id: str, quality_match: dict, target: int = TARGET_PER_PALIER) -> dict:
    """Assigne un palier aux questions sans difficulty valide. Aucun appel IA."""
    before = await palier_distribution(db, category_id)
    candidates = [q async for q in db.questions.find(
        {"category_id": category_id, "quality": quality_match, "$or": UNTAGGED_OR},
        {"id": 1, "_id": 0},
    )]
    dist = dict(before)
    per_palier = {p: 0 for p in PALIERS}
    tagged = 0
    for q in candidates:
        best = pick_palier(dist, target)
        if best is None:
            break
        r = await db.questions.update_one({"id": q["id"]}, {"$set": {"difficulty": best}})
        if r.modified_count:
            dist[best] += 1
            per_palier[best] += 1
            tagged += 1
    return {
        "candidates_found": len(candidates),
        "tagged": tagged,
        "candidates_remaining": max(0, len(candidates) - tagged),
        "distribution_before": before,
        "distribution_after": dist,
        "per_palier_added": per_palier,
        "still_missing_slots": missing_slots(dist, target),
    }


class JobCheckpoint:
    """Côté subprocess : lit l'état du job et écrit la progression après chaque
    unité de travail. Si le job n'est plus le nôtre (annulé, re-planifié après
    restart → nouveau segment_id), `save` renvoie False et le script s'arrête."""

    def __init__(self, db):
        self.db = db
        self.job_id = os.environ.get("QA_JOB_ID")
        self.segment_id = os.environ.get("QA_SEGMENT_ID")
        self.audit_since = float(os.environ.get("QA_AUDIT_SINCE") or 0) or None
        self.progress: dict = {}

    async def load(self) -> dict:
        if self.job_id:
            job = await self.db.qa_jobs.find_one({"id": self.job_id}, {"_id": 0, "progress": 1})
            self.progress = dict((job or {}).get("progress") or {})
        return self.progress

    async def save(self, **fields) -> bool:
        self.progress.update(fields)
        if not self.job_id:
            return True
        r = await self.db.qa_jobs.update_one(
            {"id": self.job_id, "segment_id": self.segment_id, "status": "running"},
            {"$set": {"progress": self.progress, "checkpoint_at": time.time()}},
        )
        return r.matched_count == 1


# Règles éditoriales propres à certaines catégories (génération + contrôle).
CATEGORY_RULES = {
    "bien-vieillir": (
        "RÈGLES ÉDITORIALES « Bien vieillir » (impératives) : on parle uniquement de conseils, "
        "d'habitudes de vie et de culture générale (alimentation, sommeil, activité physique douce, "
        "lien social, jeux de mémoire, repères culturels sur l'âge et la longévité). "
        "INTERDIT : toute allégation médicale — ne jamais écrire qu'une habitude prévient, réduit le risque, "
        "soigne ou guérit une maladie ; aucun médicament, vaccin, dosage, diagnostic, symptôme ni nom de "
        "maladie présenté comme évitable. Préférer « aide à se sentir en forme », « est conseillé pour garder "
        "le moral », « favorise un bon sommeil »."
    ),
}


def category_rules(category_id: str | None) -> str:
    rule = CATEGORY_RULES.get(category_id or "")
    return f"\n\n{rule}\n" if rule else ""


def fact_check_rules(category_id: str | None) -> str:
    if category_id not in CATEGORY_RULES:
        return ""
    return ("\n\nCONTRÔLE ÉDITORIAL : si la question, une option ou l'explication contient une allégation "
            "médicale (prévention, réduction de risque, traitement ou guérison d'une maladie, médicament, "
            "vaccin, dosage, diagnostic), réponds verdict \"wrong\" avec comment \"allégation médicale\".")
