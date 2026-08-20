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
    """Répartition qualité par catégorie, avec couverture des 7 paliers (20 questions/palier)."""
    cats = await db.categories.find({}, {"_id": 0, "id": 1, "title": 1}).to_list(50)
    out = []
    for c in cats:
        cat_id = c["id"]
        total = await db.questions.count_documents({"category_id": cat_id})
        verified = await db.questions.count_documents({"category_id": cat_id, "quality": "verified"})
        flagged = await db.questions.count_documents({"category_id": cat_id, "quality": "flagged"})
        unchecked = total - verified - flagged

        # Couverture par palier (difficulty 1..7) — 20 attendues par palier
        pipeline = [
            {"$match": {"category_id": cat_id, "quality": {"$ne": "flagged"},
                        "difficulty": {"$gte": 1, "$lte": 7}}},
            {"$group": {"_id": "$difficulty", "n": {"$sum": 1}}},
        ]
        by_diff = {d["_id"]: d["n"] async for d in db.questions.aggregate(pipeline)}
        paliers = [{"palier": d, "count": by_diff.get(d, 0), "target": 20,
                    "missing": max(0, 20 - by_diff.get(d, 0))} for d in range(1, 8)]
        missing_total = sum(p["missing"] for p in paliers)
        untagged = await db.questions.count_documents(
            {"category_id": cat_id, "quality": {"$ne": "flagged"}, "difficulty": {"$exists": False}}
        )
        out.append({
            "category_id": cat_id,
            "category_title": c["title"],
            "total": total,
            "verified": verified,
            "flagged": flagged,
            "unchecked": unchecked,
            "playable_pct": round((verified + unchecked) / total * 100) if total else 0,
            "paliers": paliers,
            "missing_for_full_parcours": missing_total,
            "untagged_playable": untagged,
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
_TOPUP_SCRIPT = _BACKEND_DIR / "topup_paliers.py"

# Limite le nombre de jobs Opus/Sonnet simultanés — au-delà, mémoire pod
# saturée (les crashes du 20/08 ont montré que 8 jobs en parallèle tuent tout
# le monde silencieusement). Chansons seul est passé en 3'53" — on garde 2.
_MAX_CONCURRENT_QA_JOBS = 2
_SUBPROCESS_TIMEOUT_SEC = 15 * 60  # timeout dur pour un audit / topup


def _pid_alive(pid: int | None) -> bool:
    """Retourne True si le PID pointe encore vers un processus vivant.
    `os.kill(pid, 0)` ne tue pas — c'est un test sans effet. On traite les
    3 causes possibles d'échec (mauvais type, PID invalide, processus mort)
    comme « processus mort »."""
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


async def _reap_dead_jobs() -> int:
    """Balaye les jobs `running` dont le PID est mort et les passe en `failed`.
    Retourne le nombre de jobs nettoyés. À appeler avant tout contrôle 409."""
    now_iso = datetime.now(timezone.utc).isoformat()
    reaped = 0
    async for j in db.qa_jobs.find({"status": "running"}, {"id": 1, "pid": 1}):
        pid = j.get("pid")
        # Si pas de PID (job pas encore démarré) OU PID mort → on passe en failed
        if pid is None or not _pid_alive(pid):
            r = await db.qa_jobs.update_one(
                {"id": j["id"], "status": "running"},
                {"$set": {
                    "status": "failed",
                    "return_code": -1,
                    "finished_at": now_iso,
                    "error": "process not alive (reaped)",
                }},
            )
            reaped += r.modified_count
    return reaped


async def sweep_running_jobs_on_startup() -> int:
    """Handler startup — passe INCONDITIONNELLEMENT tous les jobs `running`
    à `failed`. Après un restart, les PID d'avant sont morts ET peuvent avoir
    été réattribués à d'autres processus — donc pas de PID check ici."""
    now_iso = datetime.now(timezone.utc).isoformat()
    r = await db.qa_jobs.update_many(
        {"status": "running"},
        {"$set": {
            "status": "failed",
            "return_code": -1,
            "finished_at": now_iso,
            "error": "process killed by backend restart (startup sweep)",
        }},
    )
    if r.modified_count:
        from core import logger
        logger.info(f"[qa-jobs] startup sweep — {r.modified_count} job(s) running → failed")
    return r.modified_count


async def _count_running() -> int:
    return await db.qa_jobs.count_documents({"status": "running"})


async def _run_qa_subprocess(job_id: str, category_id: str, script_path: Path) -> None:
    """Lance un script d'admin QA (audit ou topup) en subprocess détaché.
    Met à jour le statut du job en DB (running → done / failed / timeout) à la fin.
    Timeout dur à `_SUBPROCESS_TIMEOUT_SEC` — au-delà, on kill et on marque failed.
    """
    log_path = f"/tmp/qa_job_{job_id}.log"
    env = os.environ.copy()
    env["ONLY_CATEGORY"] = category_id
    now_iso = lambda: datetime.now(timezone.utc).isoformat()  # noqa: E731

    proc = None
    try:
        with open(log_path, "w") as logf:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(script_path),
                cwd=str(_BACKEND_DIR),
                env=env,
                stdout=logf,
                stderr=logf,
            )
            await db.qa_jobs.update_one({"id": job_id}, {"$set": {"pid": proc.pid}})
            try:
                rc = await asyncio.wait_for(proc.wait(), timeout=_SUBPROCESS_TIMEOUT_SEC)
            except asyncio.TimeoutError:
                # Timeout — on kill le subprocess et on marque failed
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
                await db.qa_jobs.update_one({"id": job_id}, {"$set": {
                    "status": "failed",
                    "return_code": -2,
                    "log_path": log_path,
                    "finished_at": now_iso(),
                    "error": f"timeout after {_SUBPROCESS_TIMEOUT_SEC}s",
                }})
                return
        status = "done" if rc == 0 else "failed"
        await db.qa_jobs.update_one({"id": job_id}, {"$set": {
            "status": status,
            "return_code": rc,
            "log_path": log_path,
            "finished_at": now_iso(),
        }})
    except Exception as e:
        await db.qa_jobs.update_one({"id": job_id}, {"$set": {
            "status": "failed",
            "error": str(e)[:400],
            "log_path": log_path,
            "finished_at": now_iso(),
        }})
    finally:
        # Après completion, on tente de dépiler un job "queued" (sérialisation)
        asyncio.create_task(_dequeue_next())


async def _dequeue_next() -> None:
    """Si un slot se libère (< _MAX_CONCURRENT_QA_JOBS jobs running), démarre
    le prochain job `queued` (FIFO par started_at)."""
    while True:
        # Nettoyage préventif avant chaque dépilage
        await _reap_dead_jobs()
        if await _count_running() >= _MAX_CONCURRENT_QA_JOBS:
            return
        next_job = await db.qa_jobs.find_one(
            {"status": "queued"},
            sort=[("started_at", 1)],
        )
        if not next_job:
            return
        r = await db.qa_jobs.update_one(
            {"id": next_job["id"], "status": "queued"},
            {"$set": {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()}},
        )
        if r.modified_count == 0:
            continue  # race : un autre worker l'a déjà pris
        script_path = _AUDIT_SCRIPT if next_job.get("kind") == "rerun" else _TOPUP_SCRIPT
        asyncio.create_task(_run_qa_subprocess(next_job["id"], next_job["category_id"], script_path))


@router.post("/rerun/{category_id}")
async def qa_rerun(category_id: str, admin: dict = Depends(get_admin_user)) -> dict:
    """Relance le pipeline fact-check/régen pour une catégorie.

    - Refuse si un job "running" ou "queued" existe déjà pour cette catégorie.
    - Avant le contrôle 409, purge automatiquement les jobs zombies (PID mort).
    - Lance le script en subprocess ou file d'attente si trop de jobs en parallèle.
    """
    return await _launch_qa_job(category_id, admin, "rerun", _AUDIT_SCRIPT, action_label="qa.rerun")


@router.post("/topup/{category_id}")
async def qa_topup(category_id: str, admin: dict = Depends(get_admin_user)) -> dict:
    """Lance le top-up des paliers : génère les questions manquantes pour
    atteindre 20 par difficulté (Mistral/Sonnet + Opus fact-check)."""
    return await _launch_qa_job(category_id, admin, "topup", _TOPUP_SCRIPT, action_label="qa.topup")


async def _launch_qa_job(category_id: str, admin: dict, kind: str,
                         script_path: Path, action_label: str) -> dict:
    cat = await db.categories.find_one({"id": category_id})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie inconnue")

    # Purge des zombies AVANT le contrôle anti-doublon (le point-clé du fix)
    reaped = await _reap_dead_jobs()
    if reaped:
        from core import logger
        logger.info(f"[qa-jobs] lancement {category_id}: {reaped} zombie(s) nettoyé(s)")

    existing = await db.qa_jobs.find_one(
        {"category_id": category_id, "status": {"$in": ["running", "queued"]}}
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Job déjà {existing['status']} pour {category_id} (id={existing['id']})",
        )

    import uuid
    job_id = str(uuid.uuid4())
    running_count = await _count_running()
    # Sérialisation : au-delà de la limite, on met en file d'attente
    initial_status = "running" if running_count < _MAX_CONCURRENT_QA_JOBS else "queued"

    job_doc = {
        "id": job_id,
        "category_id": category_id,
        "category_title": cat.get("title"),
        "kind": kind,
        "status": initial_status,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "started_by": admin.get("email"),
    }
    await db.qa_jobs.insert_one(job_doc)
    await record_audit(admin, action=action_label, target_type="category", target_id=category_id,
                       target_label=cat.get("title"),
                       meta={"job_id": job_id, "kind": kind, "initial_status": initial_status})

    if initial_status == "running":
        asyncio.create_task(_run_qa_subprocess(job_id, category_id, script_path))
    # else : le job restera "queued" et sera dépilé automatiquement quand un
    # slot se libère via _dequeue_next() (finally d'un job qui se termine).

    job_doc.pop("_id", None)
    return {"ok": True, "job": job_doc, "queued": initial_status == "queued",
            "running_count": running_count, "max_concurrent": _MAX_CONCURRENT_QA_JOBS}


@router.get("/jobs")
async def qa_jobs(_: dict = Depends(get_admin_user), limit: int = Query(20, ge=1, le=100)) -> list[dict]:
    """Liste les jobs de fact-check récents (running/queued/done/failed).
    Nettoie les zombies au passage pour que l'admin ne voit plus de fantômes."""
    await _reap_dead_jobs()
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
