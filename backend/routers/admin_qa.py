"""Admin QA — pilotage du fact-check et modération des questions IA.

Endpoints (rôle admin requis) :
    GET  /admin/qa/summary              : résumé par catégorie
    GET  /admin/qa/questions            : liste paginée + recherche par mot-clé
    POST /admin/qa/{id}/approve         : force flagged → verified
    POST /admin/qa/{id}/flag            : force → flagged
    POST /admin/qa/{id}/apply-correction: applique la correction fact-check
    DELETE /admin/qa/{id}               : supprime la question
    POST /admin/qa/rerun/{category_id}  : relance le pipeline fact-check pour 1 catégorie
    GET  /admin/qa/jobs                 : liste des runs récents avec statut
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core import db, get_admin_user, record_audit

router = APIRouter(prefix="/admin/qa", tags=["admin-qa"])


@router.get("/summary")
async def qa_summary(_: dict = Depends(get_admin_user)) -> list[dict]:
    """Répartition qualité par catégorie."""
    cats = await db.categories.find({}, {"_id": 0, "id": 1, "title": 1}).to_list(50)
    out = []
    for c in cats:
        cat_id = c["id"]
        total = await db.questions.count_documents({"category_id": cat_id})
        verified = await db.questions.count_documents({"category_id": cat_id, "quality": "verified"})
        flagged = await db.questions.count_documents({"category_id": cat_id, "quality": "flagged"})
        unchecked = total - verified - flagged
        out.append({
            "category_id": cat_id,
            "category_title": c["title"],
            "total": total,
            "verified": verified,
            "flagged": flagged,
            "unchecked": unchecked,
            "playable_pct": round((verified + unchecked) / total * 100) if total else 0,
        })
    return out


@router.get("/questions")
async def qa_questions(
    _: dict = Depends(get_admin_user),
    category_id: str | None = None,
    quality: Literal["verified", "flagged", "unchecked", "all"] = "flagged",
    q: str | None = Query(None, max_length=120, description="Recherche mot-clé (question / options / commentaire fact-check)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Liste paginée des questions avec statut fact-check + recherche par mot-clé.

    Le paramètre `q` cherche insensible à la casse dans :
      - le texte de la question
      - les 4 options
      - le commentaire du fact-check (fact_check.comment)
    """
    query: dict = {}
    if category_id:
        query["category_id"] = category_id
    if quality == "verified":
        query["quality"] = "verified"
    elif quality == "flagged":
        query["quality"] = "flagged"
    elif quality == "unchecked":
        query["quality"] = {"$exists": False}
    # "all" → pas de filtre quality

    if q:
        # Escape des méta-caractères regex pour éviter injections
        import re as _re
        needle = _re.escape(q.strip())
        query["$or"] = [
            {"question": {"$regex": needle, "$options": "i"}},
            {"options": {"$regex": needle, "$options": "i"}},
            {"fact_check.comment": {"$regex": needle, "$options": "i"}},
            {"fact_check.correction": {"$regex": needle, "$options": "i"}},
        ]

    total = await db.questions.count_documents(query)
    docs = await db.questions.find(query, {"_id": 0}).sort([("fact_check.confidence", 1), ("id", 1)]).skip(offset).limit(limit).to_list(limit)
    return {"total": total, "limit": limit, "offset": offset, "questions": docs}


class ApproveBody(BaseModel):
    reason: str = Field("", max_length=300)


class BulkBody(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=500, description="Liste d'IDs de questions à traiter")


# ⚠️ Les routes /bulk/* DOIVENT être déclarées avant /{qid}/* — sinon FastAPI
# route /bulk/approve vers /{qid}/approve avec qid="bulk".
@router.post("/bulk/approve")
async def qa_bulk_approve(body: BulkBody, admin: dict = Depends(get_admin_user)) -> dict:
    """Approuve en masse : marque toutes les questions listées en `verified`."""
    r = await db.questions.update_many(
        {"id": {"$in": body.ids}},
        {"$set": {
            "quality": "verified",
            "fact_check.admin_override": {
                "action": "bulk_approved",
                "by": admin.get("email"),
                "count": len(body.ids),
            },
        }},
    )
    await record_audit(admin, action="qa.bulk_approve", target_type="questions",
                       meta={"requested": len(body.ids), "modified": r.modified_count, "ids": body.ids[:20]})
    return {"ok": True, "requested": len(body.ids), "matched": r.matched_count, "modified": r.modified_count}


@router.post("/bulk/delete")
async def qa_bulk_delete(body: BulkBody, admin: dict = Depends(get_admin_user)) -> dict:
    """Supprime en masse. Aucun undo — l'UI doit demander confirmation."""
    r = await db.questions.delete_many({"id": {"$in": body.ids}})
    await record_audit(admin, action="qa.bulk_delete", target_type="questions",
                       meta={"requested": len(body.ids), "deleted": r.deleted_count, "ids": body.ids[:20]})
    return {"ok": True, "requested": len(body.ids), "deleted": r.deleted_count}


@router.post("/bulk/flag")
async def qa_bulk_flag(body: BulkBody, admin: dict = Depends(get_admin_user)) -> dict:
    """Flag en masse : retire les questions listées du tirage."""
    r = await db.questions.update_many(
        {"id": {"$in": body.ids}},
        {"$set": {
            "quality": "flagged",
            "fact_check.admin_override": {
                "action": "bulk_flagged",
                "by": admin.get("email"),
                "count": len(body.ids),
            },
        }},
    )
    await record_audit(admin, action="qa.bulk_flag", target_type="questions",
                       meta={"requested": len(body.ids), "modified": r.modified_count, "ids": body.ids[:20]})
    return {"ok": True, "requested": len(body.ids), "matched": r.matched_count, "modified": r.modified_count}


@router.post("/{qid}/approve")
async def qa_approve(qid: str, body: ApproveBody, admin: dict = Depends(get_admin_user)) -> dict:
    """Force une question `flagged` → `verified` (le tirage la reprendra)."""
    r = await db.questions.update_one(
        {"id": qid},
        {"$set": {
            "quality": "verified",
            "fact_check.admin_override": {
                "action": "approved",
                "by": admin.get("email"),
                "reason": body.reason,
            },
        }},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Question introuvable")
    return {"ok": True}


@router.post("/{qid}/flag")
async def qa_flag(qid: str, body: ApproveBody, admin: dict = Depends(get_admin_user)) -> dict:
    """Force une question → `flagged` (retire du tirage)."""
    r = await db.questions.update_one(
        {"id": qid},
        {"$set": {
            "quality": "flagged",
            "fact_check.admin_override": {
                "action": "flagged",
                "by": admin.get("email"),
                "reason": body.reason,
            },
        }},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Question introuvable")
    return {"ok": True}


class CorrectionBody(BaseModel):
    """Correction manuelle éventuelle : si fournie, remplace la question."""
    question: str | None = None
    options: list[str] | None = None
    correct_index: int | None = Field(None, ge=0, le=3)
    explanation: str | None = None


@router.post("/{qid}/apply-correction")
async def qa_apply_correction(
    qid: str,
    body: CorrectionBody,
    admin: dict = Depends(get_admin_user),
) -> dict:
    """Applique la correction proposée par le fact-check (ou une correction manuelle
    dans le payload) et remet la question en `verified`.
    """
    doc = await db.questions.find_one({"id": qid})
    if not doc:
        raise HTTPException(status_code=404, detail="Question introuvable")

    updates: dict = {"quality": "verified"}
    fact = doc.get("fact_check") or {}

    # 1) Correction textuelle proposée par le fact-check → on met à jour la bonne réponse
    if fact.get("correction") and not (body.options or body.question):
        # On sauvegarde l'original avant modification
        updates["original_snapshot"] = {
            "question": doc["question"],
            "options": doc["options"],
            "correct_index": doc["correct_index"],
        }
        # Trouver l'option qui correspond à la correction (best-effort)
        correction = str(fact["correction"]).strip().lower()
        matched = None
        for i, opt in enumerate(doc["options"]):
            if correction in opt.lower() or opt.lower() in correction:
                matched = i
                break
        if matched is not None:
            updates["correct_index"] = matched
        else:
            # Correction texte libre → remplace l'option incorrecte par la correction
            new_opts = list(doc["options"])
            new_opts[doc["correct_index"]] = fact["correction"]
            updates["options"] = new_opts
        updates["explanation"] = f"{doc.get('explanation', '')} — corrigé après fact-check ({fact.get('checker_model', 'llm')})."

    # 2) Correction manuelle fournie explicitement
    if body.question:
        updates["question"] = body.question
    if body.options and len(body.options) == 4:
        updates["options"] = body.options
    if body.correct_index is not None:
        updates["correct_index"] = body.correct_index
    if body.explanation:
        updates["explanation"] = body.explanation

    updates["fact_check.admin_override"] = {
        "action": "corrected",
        "by": admin.get("email"),
    }

    await db.questions.update_one({"id": qid}, {"$set": updates})
    return {"ok": True, "updated_fields": list(updates.keys())}


@router.delete("/{qid}")
async def qa_delete(qid: str, admin: dict = Depends(get_admin_user)) -> dict:
    r = await db.questions.delete_one({"id": qid})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Question introuvable")
    await record_audit(admin, action="qa.delete", target_type="question", target_id=qid)
    return {"ok": True}

# =============================================================================
# Bulk actions — approbation ou suppression massive
# =============================================================================





# =============================================================================
# Regen batch — relance du pipeline fact-check pour une catégorie
# =============================================================================

# Un seul job à la fois par catégorie pour éviter la double-consommation LLM.
# Les jobs sont stockés dans MongoDB `qa_jobs` pour survivre à un restart.
_BACKEND_DIR = Path(__file__).parent.parent
_AUDIT_SCRIPT = _BACKEND_DIR / "audit_and_regen_questions.py"


async def _run_audit_subprocess(job_id: str, category_id: str) -> None:
    """Lance le script d'audit en subprocess Python détaché. Met à jour le
    statut du job en DB (running → done / failed) à la fin.
    """
    log_path = f"/tmp/qa_job_{job_id}.log"
    env = os.environ.copy()
    env["ONLY_CATEGORY"] = category_id

    try:
        with open(log_path, "w") as logf:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(_AUDIT_SCRIPT),
                cwd=str(_BACKEND_DIR),
                env=env,
                stdout=logf,
                stderr=logf,
            )
            await db.qa_jobs.update_one({"id": job_id}, {"$set": {"pid": proc.pid}})
            rc = await proc.wait()
        status = "done" if rc == 0 else "failed"
        await db.qa_jobs.update_one({"id": job_id}, {"$set": {
            "status": status,
            "return_code": rc,
            "log_path": log_path,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }})
    except Exception as e:
        await db.qa_jobs.update_one({"id": job_id}, {"$set": {
            "status": "failed",
            "error": str(e)[:400],
            "log_path": log_path,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }})


@router.post("/rerun/{category_id}")
async def qa_rerun(category_id: str, admin: dict = Depends(get_admin_user)) -> dict:
    """Relance le pipeline fact-check/régen pour une catégorie.

    - Refuse si un job "running" existe déjà pour cette catégorie (anti-double-facturation LLM).
    - Lance le script en subprocess Python non bloquant. Le statut se lit via `/admin/qa/jobs`.
    """
    cat = await db.categories.find_one({"id": category_id})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie inconnue")

    existing = await db.qa_jobs.find_one({"category_id": category_id, "status": "running"})
    if existing:
        raise HTTPException(status_code=409, detail=f"Job déjà en cours pour {category_id} (id={existing['id']})")

    import uuid
    job_id = str(uuid.uuid4())
    job_doc = {
        "id": job_id,
        "category_id": category_id,
        "category_title": cat.get("title"),
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "started_by": admin.get("email"),
    }
    await db.qa_jobs.insert_one(job_doc)
    await record_audit(admin, action="qa.rerun", target_type="category", target_id=category_id,
                       target_label=cat.get("title"), meta={"job_id": job_id})

    # Fire-and-forget : le task tourne en arrière-plan, on rend la main immédiatement.
    asyncio.create_task(_run_audit_subprocess(job_id, category_id))

    job_doc.pop("_id", None)
    return {"ok": True, "job": job_doc}


@router.get("/jobs")
async def qa_jobs(_: dict = Depends(get_admin_user), limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    """Liste les jobs de fact-check récents (running/done/failed)."""
    docs = await db.qa_jobs.find({}, {"_id": 0}).sort("started_at", -1).limit(limit).to_list(limit)
    # Enrichit avec un aperçu des dernières lignes de log pour les jobs récents
    for j in docs:
        if j.get("log_path") and os.path.exists(j["log_path"]):
            try:
                with open(j["log_path"]) as f:
                    lines = f.readlines()
                    j["log_tail"] = "".join(lines[-6:])[-800:]
            except Exception:
                pass
    return docs
