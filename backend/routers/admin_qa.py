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
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core import db, get_admin_user, record_audit, logger
from qa_pipeline import retag_untagged

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

# Timeouts durs par type de job. Le RERUN (audit complet de 200+ questions)
# tourne facilement 11-13 min sur les grosses catégories (Histoire de France,
# Objets d'antan) — 15 min était trop juste et provoquait des timeouts alors
# que le duo Mistral+Opus tournait normalement. Le TOPUP reste à 15 min car
# il ne génère que les manquantes (typiquement 20-40 questions).
_TIMEOUT_BY_KIND: dict[str, int] = {
    "topup": 15 * 60,   # 15 min
    "rerun": 30 * 60,   # 30 min — audit complet volumineux
}
_SUBPROCESS_TIMEOUT_SEC_DEFAULT = 15 * 60  # fallback si kind inconnu

# Reprise auto (A3) : un job interrompu (timeout avec progression, restart,
# OOM) est remis en file et repart de son checkpoint. Plafond de reprises.
_MAX_RESUMES = 3
_WATCHDOG_INTERVAL_SEC = 60


def _pid_alive(pid: int | None) -> bool:
    """⚠️ NE PAS UTILISER pour tester la vivacité d'un job — voir `_reap_dead_jobs`
    qui s'appuie désormais sur `last_heartbeat_at`. Conservée uniquement pour
    cibler un SIGTERM lors d'un cancel manuel (usage sûr : la cible est un PID
    qu'on veut tuer, pas prouver vivant)."""
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


# ===== Supervision heartbeat =====
# Le parent écrit `last_heartbeat_at` toutes les _HEARTBEAT_INTERVAL_SEC
# secondes tant que le subprocess est vivant. Le reaper considère un job
# mort si le heartbeat a dépassé _HEARTBEAT_TIMEOUT_SEC. Grâce de
# _HEARTBEAT_GRACE_SEC après started_at avant tout contrôle.
_HEARTBEAT_INTERVAL_SEC = 15
_HEARTBEAT_TIMEOUT_SEC = 180  # 3 min sans battement = mort
_HEARTBEAT_GRACE_SEC = 60     # 1 min de grâce après started_at


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _heartbeat_loop(job_id: str, proc) -> None:
    """Écrit un heartbeat toutes les 15 s tant que le subprocess vit.
    Filtre atomique `status=running` — n'écrit jamais sur un job terminal.
    """
    while proc.returncode is None:
        await db.qa_jobs.update_one(
            {"id": job_id, "status": "running"},
            {"$set": {"last_heartbeat_at": _now_iso()}},
        )
        try:
            await asyncio.sleep(_HEARTBEAT_INTERVAL_SEC)
        except asyncio.CancelledError:
            return


async def _resume_or_fail(job_id: str, reason: str, return_code: int,
                          require_progress: bool = False) -> str:
    """Job `running` interrompu → remis en `queued` (reprise depuis checkpoint)
    tant que le plafond n'est pas atteint, sinon `failed`. Ne touche jamais un
    état terminal. Retourne "resumed" | "failed" | "terminal"."""
    job = await db.qa_jobs.find_one(
        {"id": job_id, "status": "running"},
        {"_id": 0, "resume_count": 1, "progress": 1, "segment_start_done": 1},
    )
    if not job:
        return "terminal"
    n = int(job.get("resume_count") or 0)
    done = int((job.get("progress") or {}).get("done") or 0)
    progressed = done > int(job.get("segment_start_done") or 0)
    if n < _MAX_RESUMES and (progressed or not require_progress):
        r = await db.qa_jobs.update_one(
            {"id": job_id, "status": "running"},
            {"$set": {"status": "queued", "resume_count": n + 1,
                      "last_interruption": reason, "last_interruption_at": _now_iso()},
             "$unset": {"pid": "", "last_heartbeat_at": "", "segment_id": ""}},
        )
        if r.modified_count:
            logger.info(f"[qa-jobs] {job_id} interrompu ({reason}) → reprise {n + 1}/{_MAX_RESUMES}")
            return "resumed"
        return "terminal"
    if n >= _MAX_RESUMES:
        reason = f"{reason} — {n} reprise(s) épuisée(s)"
    else:
        reason = f"{reason} — aucune progression"
    r = await db.qa_jobs.update_one(
        {"id": job_id, "status": "running"},
        {"$set": {"status": "failed", "return_code": return_code,
                  "finished_at": _now_iso(), "error": reason},
         "$unset": {"segment_id": ""}},
    )
    return "failed" if r.modified_count else "terminal"


async def _reap_dead_jobs() -> int:
    """Passe en `failed` les jobs `running` dont le heartbeat est trop vieux.

    Règles strictes (audit 21/08/2026) :
      1. Grâce absolue de 60 s après `started_at` — aucun job ne peut être
         reaped avant, quelle que soit la raison.
      2. Après la grâce : reap seulement si `last_heartbeat_at` est absent
         (subprocess jamais monté) OU trop vieux (> 180 s sans battement).
      3. Filtre atomique `{status: "running"}` — aucun état terminal
         (done / failed / cancelled) ne peut être écrasé.
      4. Aucun test de vivacité par PID nu — PID peu fiable en Kubernetes.
    """
    now = datetime.now(timezone.utc)
    reaped = 0
    async for j in db.qa_jobs.find(
        {"status": "running"},
        {"id": 1, "started_at": 1, "last_heartbeat_at": 1},
    ):
        # 1) Grâce après started_at
        try:
            started = datetime.fromisoformat(j["started_at"])
            age_sec = (now - started).total_seconds()
        except (KeyError, ValueError, TypeError):
            age_sec = 999.0
        if age_sec < _HEARTBEAT_GRACE_SEC:
            continue

        # 2) Heartbeat check
        hb_iso = j.get("last_heartbeat_at")
        if hb_iso is None:
            reason = f"no heartbeat after {int(age_sec)}s"
        else:
            try:
                hb = datetime.fromisoformat(hb_iso)
                hb_age = (now - hb).total_seconds()
            except (ValueError, TypeError):
                hb_age = 999.0
            if hb_age < _HEARTBEAT_TIMEOUT_SEC:
                continue  # heartbeat récent → job vivant
            reason = f"heartbeat stale ({int(hb_age)}s ago)"

        # 3) Reprise depuis checkpoint (ou failed si plafond atteint)
        if await _resume_or_fail(j["id"], reason, -1) != "terminal":
            reaped += 1
    return reaped


async def sweep_running_jobs_on_startup() -> int:
    """Handler startup — passe en `failed` uniquement les jobs `running` dont
    le heartbeat est stale (> 3 min). Ne touche JAMAIS un état terminal.

    ⚠️ Correctif audit 21/08 : avant, tous les running étaient inconditionnellement
    marqués failed avec un `error`, écrasant des jobs qui allaient légitimement
    être finalisés à `done` par le parent. Maintenant : sweep conditionné par
    l'ancienneté du heartbeat, filtre atomique `status=running`.
    """
    now = datetime.now(timezone.utc)
    reaped = 0
    async for j in db.qa_jobs.find(
        {"status": "running"},
        {"id": 1, "started_at": 1, "last_heartbeat_at": 1},
    ):
        hb_iso = j.get("last_heartbeat_at")
        if hb_iso is None:
            try:
                started = datetime.fromisoformat(j["started_at"])
                age_sec = (now - started).total_seconds()
            except (KeyError, ValueError, TypeError):
                age_sec = 999.0
            if age_sec < _HEARTBEAT_TIMEOUT_SEC:
                continue
            reason = f"startup sweep — no heartbeat after {int(age_sec)}s"
        else:
            try:
                hb = datetime.fromisoformat(hb_iso)
                hb_age = (now - hb).total_seconds()
            except (ValueError, TypeError):
                hb_age = 999.0
            if hb_age < _HEARTBEAT_TIMEOUT_SEC:
                continue
            reason = f"startup sweep — heartbeat stale ({int(hb_age)}s)"

        if await _resume_or_fail(j["id"], reason, -1) != "terminal":
            reaped += 1

    if reaped:
        logger.info(f"[qa-jobs] startup sweep — {reaped} job(s) running stale → reprise/failed")
    return reaped


async def qa_watchdog_loop() -> None:
    """Toutes les 60 s : reprend les jobs au heartbeat mort et dépile la file.
    Indispensable après un restart (plus aucun parent pour finaliser)."""
    while True:
        try:
            await asyncio.sleep(_WATCHDOG_INTERVAL_SEC)
            await _dequeue_next()
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning(f"[qa-watchdog] {type(e).__name__}: {e}")


async def _count_running() -> int:
    return await db.qa_jobs.count_documents({"status": "running"})


async def _run_qa_subprocess(job_id: str, category_id: str, script_path: Path, kind: str = "topup") -> None:
    """Lance un script d'admin QA (audit ou topup) en subprocess détaché.
    Écrit un heartbeat toutes les 15 s dans le doc du job (voir `_heartbeat_loop`).
    Met à jour le statut (running → done / failed / timeout) atomiquement en
    filtrant sur `status=running` — les états terminaux ne sont jamais écrasés.

    Le timeout dur dépend du `kind` : topup=15 min, rerun=30 min (audit complet).
    """
    log_path = f"/tmp/qa_job_{job_id}.log"
    timeout_sec = _TIMEOUT_BY_KIND.get(kind, _SUBPROCESS_TIMEOUT_SEC_DEFAULT)

    # Nouveau segment : le subprocess n'écrit ses checkpoints que si le job
    # porte encore SON segment_id (sinon il s'arrête : annulé / re-planifié).
    job = await db.qa_jobs.find_one({"id": job_id}, {"_id": 0}) or {}
    segment_id = uuid.uuid4().hex
    audit_since = job.get("created_at")
    if not audit_since:
        try:
            audit_since = datetime.fromisoformat(job["started_at"]).timestamp()
        except (KeyError, ValueError, TypeError):
            audit_since = time.time()
    await db.qa_jobs.update_one(
        {"id": job_id, "status": "running"},
        {"$set": {"segment_id": segment_id,
                  "segment_start_done": int((job.get("progress") or {}).get("done") or 0)}},
    )
    env = os.environ.copy()
    env.update({"ONLY_CATEGORY": category_id, "QA_JOB_ID": job_id,
                "QA_SEGMENT_ID": segment_id, "QA_AUDIT_SINCE": str(audit_since)})

    proc = None
    hb_task = None
    try:
        with open(log_path, "a") as logf:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, str(script_path),
                cwd=str(_BACKEND_DIR),
                env=env,
                stdout=logf,
                stderr=logf,
            )
            # PID + premier heartbeat immédiatement pour éviter la fenêtre nue
            await db.qa_jobs.update_one(
                {"id": job_id, "status": "running"},
                {"$set": {"pid": proc.pid, "last_heartbeat_at": _now_iso()}},
            )
            hb_task = asyncio.create_task(_heartbeat_loop(job_id, proc))
            try:
                rc = await asyncio.wait_for(proc.wait(), timeout=timeout_sec)
            except asyncio.TimeoutError:
                # Timeout — on kill le subprocess et on marque failed
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
                # Reprise depuis checkpoint si ce segment a progressé, sinon failed
                await db.qa_jobs.update_one({"id": job_id}, {"$set": {"log_path": log_path}})
                await _resume_or_fail(job_id, f"timeout after {timeout_sec}s ({kind})", -2,
                                      require_progress=True)
                return
        if rc < 0:
            # Tué par un signal (OOM, restart…) hors annulation → reprise
            await db.qa_jobs.update_one({"id": job_id}, {"$set": {"log_path": log_path}})
            await _resume_or_fail(job_id, f"killed by signal {-rc}", rc)
            return
        status = "done" if rc == 0 else "failed"
        # Update finalisation : filtre `status=running` (préserve terminal atomique)
        # + $unset error pour effacer tout marquage laissé par un reaper race'd
        update_doc = {
            "$set": {
                "status": status,
                "return_code": rc,
                "log_path": log_path,
                "finished_at": _now_iso(),
            },
        }
        update_doc["$unset"] = {"segment_id": ""}
        if rc == 0:
            update_doc["$unset"]["error"] = ""  # succès : on efface les erreurs de race
        await db.qa_jobs.update_one(
            {"id": job_id, "status": "running"},
            update_doc,
        )
    except Exception as e:
        await db.qa_jobs.update_one(
            {"id": job_id, "status": "running"},
            {"$set": {
                "status": "failed",
                "error": str(e)[:400],
                "log_path": log_path,
                "finished_at": _now_iso(),
            }},
        )
    finally:
        if hb_task and not hb_task.done():
            hb_task.cancel()
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
        asyncio.create_task(_run_qa_subprocess(
            next_job["id"], next_job["category_id"], script_path, kind=next_job.get("kind", "topup")
        ))


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


# ============================================================================
# REBALANCE — RETAG sans IA (audit 21/08 : 780 questions vérifiées mais sans
# palier dorment en base). Assigne le champ `difficulty` (1..7) aux questions
# vérifiées non taguées, en remplissant en priorité les paliers les plus vides
# (7, 6, 5…) — pas 1, 2, 3.
# ============================================================================


@router.post("/rebalance/{category_id}")
async def qa_rebalance(category_id: str, admin: dict = Depends(get_admin_user)) -> dict:
    """RETAG sans IA — assigne les questions jouables sans palier aux paliers
    déficitaires (le plus vide d'abord, palier haut à égalité)."""
    cat = await db.categories.find_one({"id": category_id})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie inconnue")
    res = await retag_untagged(db, category_id, {"$ne": "flagged"})
    await record_audit(
        admin, action="qa.rebalance", target_type="category",
        target_id=category_id, target_label=cat.get("title"),
        meta={"tagged": res["tagged"], "still_missing": res["still_missing_slots"],
              "per_palier": res["per_palier_added"]},
    )
    return {"ok": True, "category_id": category_id, "category_title": cat.get("title"), **res}


@router.post("/rebalance-all")
async def qa_rebalance_all(admin: dict = Depends(get_admin_user)) -> dict:
    """Rebalance sur toutes les catégories en une passe. Aucun appel IA."""
    cats = await db.categories.find({}, {"id": 1, "title": 1, "_id": 0}).to_list(50)
    per_cat = []
    for cat in cats:
        res = await retag_untagged(db, cat["id"], {"$ne": "flagged"})
        per_cat.append({
            "category_id": cat["id"], "category_title": cat["title"],
            "tagged": res["tagged"], "still_missing_slots": res["still_missing_slots"],
            "distribution_after": res["distribution_after"],
        })
    total_tagged = sum(c["tagged"] for c in per_cat)
    await record_audit(
        admin, action="qa.rebalance_all", target_type="system",
        meta={"total_tagged": total_tagged, "categories": len(cats)},
    )
    return {"ok": True, "total_tagged": total_tagged, "categories": per_cat}


@router.post("/auto-seed")
async def qa_auto_seed(admin: dict = Depends(get_admin_user)) -> dict:
    """Déclenche l'auto-seed : lance un top-up pour chaque catégorie
    sous-approvisionnée (< 140 questions jouables). Idempotent — le queue
    empêche les doublons."""
    result = await auto_seed_understocked_categories()
    await record_audit(admin, action="qa.auto_seed_manual", target_type="system",
                       meta={"summary": {k: v for k, v in result.items() if k != "categories"}})
    return result


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
        "created_at": time.time(),
        "resume_count": 0,
        "started_by": admin.get("email"),
    }
    await db.qa_jobs.insert_one(job_doc)
    await record_audit(admin, action=action_label, target_type="category", target_id=category_id,
                       target_label=cat.get("title"),
                       meta={"job_id": job_id, "kind": kind, "initial_status": initial_status})

    if initial_status == "running":
        asyncio.create_task(_run_qa_subprocess(job_id, category_id, script_path, kind=kind))
    # else : le job restera "queued" et sera dépilé automatiquement quand un
    # slot se libère via _dequeue_next() (finally d'un job qui se termine).

    job_doc.pop("_id", None)
    return {"ok": True, "job": job_doc, "queued": initial_status == "queued",
            "running_count": running_count, "max_concurrent": _MAX_CONCURRENT_QA_JOBS}


async def auto_seed_understocked_categories() -> dict:
    """Détecte les catégories sous-approvisionnées (< 140 questions jouables)
    et lance automatiquement un top-up pour chacune.

    Idempotent :
      - le queue anti-doublon empêche de lancer 2 fois pour la même catégorie
      - respecte la limite `_MAX_CONCURRENT_QA_JOBS` (les surplus vont en `queued`)

    À appeler au startup après le seed des catégories. Non-bloquant : le retour
    est immédiat, les subprocess Mistral/Opus tournent en arrière-plan.

    Retourne un dict {launched, queued, skipped, already_running, cats: [...]}
    """
    from core import logger

    # Purge des zombies avant la détection
    await _reap_dead_jobs()

    cats = await db.categories.find({}, {"id": 1, "title": 1, "_id": 0}).to_list(200)
    system_admin = {"email": "system@auto-seed", "role": "admin"}
    launched, queued_c, already, skipped = 0, 0, 0, 0
    details: list[dict] = []

    for cat in cats:
        cat_id = cat["id"]
        playable = await db.questions.count_documents({
            "category_id": cat_id,
            "difficulty": {"$gte": 1, "$lte": 7},
            "quality": {"$ne": "flagged"},
        })
        if playable >= 140:
            skipped += 1
            continue
        try:
            res = await _launch_qa_job(cat_id, system_admin, "topup",
                                       _TOPUP_SCRIPT, action_label="qa.auto_seed")
            if res.get("queued"):
                queued_c += 1
            else:
                launched += 1
            details.append({"category_id": cat_id, "playable": playable,
                            "status": res["job"]["status"]})
            logger.info(f"[auto-seed] {cat_id}: {playable}/140 → {res['job']['status']}")
        except HTTPException as e:
            if e.status_code == 409:
                already += 1
                details.append({"category_id": cat_id, "playable": playable,
                                "status": "already_running_or_queued"})
                logger.debug(f"[auto-seed] {cat_id}: déjà en cours (409)")
            else:
                logger.warning(f"[auto-seed] {cat_id}: erreur {e.status_code} {e.detail}")
        except Exception as e:
            logger.warning(f"[auto-seed] {cat_id}: exception {type(e).__name__}: {e}")

    summary = {
        "launched": launched,
        "queued": queued_c,
        "already_running": already,
        "skipped_complete": skipped,
        "categories": details,
    }
    if launched or queued_c:
        logger.info(f"[auto-seed] bilan : {launched} lancé(s), {queued_c} en file, "
                    f"{already} déjà en cours, {skipped} déjà complet(s)")
    return summary


@router.post("/jobs/{job_id}/cancel")
async def qa_cancel_job(job_id: str, admin: dict = Depends(get_admin_user)) -> dict:
    """Annule un job `running` (kill du subprocess) ou `queued` (retrait file).
    Idempotent : si le job est déjà terminé, retourne 409."""
    job = await db.qa_jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    if job["status"] not in ("running", "queued"):
        raise HTTPException(status_code=409, detail=f"Job déjà {job['status']} — rien à annuler")

    now_iso = datetime.now(timezone.utc).isoformat()
    if job["status"] == "queued":
        # Retrait simple de la file
        await db.qa_jobs.update_one({"id": job_id}, {"$set": {
            "status": "cancelled",
            "finished_at": now_iso,
            "return_code": -3,
        }})
        await record_audit(admin, action="qa.cancel", target_type="qa_job",
                           target_id=job_id, target_label=job.get("category_id"),
                           meta={"was": "queued"})
        return {"ok": True, "was": "queued"}

    # running : on tue le subprocess si son PID est encore vivant
    pid = job.get("pid")
    killed = False
    if pid and _pid_alive(pid):
        try:
            os.kill(int(pid), 15)  # SIGTERM
            killed = True
        except (OSError, TypeError, ValueError):
            pass
    await db.qa_jobs.update_one({"id": job_id}, {"$set": {
        "status": "cancelled",
        "finished_at": now_iso,
        "return_code": -3,
        "error": "cancelled by admin",
    }, "$unset": {"segment_id": ""}})
    await record_audit(admin, action="qa.cancel", target_type="qa_job",
                       target_id=job_id, target_label=job.get("category_id"),
                       meta={"was": "running", "killed_pid": pid if killed else None})
    # Dépile un job en attente pour utiliser le slot libéré
    asyncio.create_task(_dequeue_next())
    return {"ok": True, "was": "running", "killed_pid": pid if killed else None}


@router.get("/queue")
async def qa_queue(_: dict = Depends(get_admin_user)) -> dict:
    """Vue focalisée sur les jobs actifs : running + queued, ordonnés,
    avec temps écoulé, position et estimation d'attente.

    Estimation basée sur la durée médiane des 10 derniers jobs `done` du même
    `kind` (rerun ou topup). Fallback : 5 min si aucune donnée."""
    await _reap_dead_jobs()

    # 1. Durée médiane par kind (10 derniers done)
    from statistics import median
    avg_by_kind: dict[str, float] = {}
    for kind in ("rerun", "topup"):
        durations: list[float] = []
        async for j in db.qa_jobs.find(
            {"kind": kind, "status": "done", "finished_at": {"$exists": True}, "started_at": {"$exists": True}},
            {"started_at": 1, "finished_at": 1, "_id": 0},
        ).sort("finished_at", -1).limit(10):
            try:
                st = datetime.fromisoformat(j["started_at"])
                ft = datetime.fromisoformat(j["finished_at"])
                durations.append((ft - st).total_seconds())
            except (ValueError, KeyError):
                continue
        avg_by_kind[kind] = median(durations) if durations else 300.0  # 5 min fallback

    # 2. Jobs actifs (running d'abord, puis queued par ordre started_at)
    running = await db.qa_jobs.find({"status": "running"}, {"_id": 0}).sort("started_at", 1).to_list(20)
    queued = await db.qa_jobs.find({"status": "queued"}, {"_id": 0}).sort("started_at", 1).to_list(20)

    # Compteur de questions jouables par catégorie pour chaque job actif
    # (playable = difficulty 1..7 ET quality != flagged). Cible = 140.
    async def _playable_count(cat_id: str) -> int:
        return await db.questions.count_documents({
            "category_id": cat_id,
            "difficulty": {"$gte": 1, "$lte": 7},
            "quality": {"$ne": "flagged"},
        })

    now = datetime.now(timezone.utc)
    running_out = []
    total_remaining_running = 0.0
    for j in running:
        try:
            st = datetime.fromisoformat(j["started_at"])
            elapsed = (now - st).total_seconds()
        except (ValueError, KeyError):
            elapsed = 0.0
        expected = avg_by_kind.get(j.get("kind"), 300.0)
        remaining = max(0.0, expected - elapsed)
        total_remaining_running += remaining
        current = await _playable_count(j["category_id"])
        running_out.append({
            **j,
            "elapsed_sec": int(elapsed),
            "expected_sec": int(expected),
            "remaining_sec": int(remaining),
            "questions_current": current,
            "questions_target": 140,
        })

    # 3. Pour chaque queued : position + estimation
    #    On assume que le prochain slot se libère quand le job en cours le plus
    #    proche de la fin termine (min des remaining).
    remainings = sorted([r["remaining_sec"] for r in running_out]) or [0]
    queued_out = []
    # pipe = liste des instants (en secondes) où un slot se libère, actualisée
    slot_free_at = list(remainings)  # secondes avant chaque libération
    for i, j in enumerate(queued):
        # Le prochain slot dispo = min de la liste
        slot_free_at.sort()
        wait_sec = slot_free_at[0]
        expected = avg_by_kind.get(j.get("kind"), 300.0)
        # Ce job occupera son slot jusqu'à wait_sec + expected
        slot_free_at[0] = wait_sec + expected
        current = await _playable_count(j["category_id"])
        queued_out.append({
            **j,
            "position": i + 1,
            "wait_before_start_sec": int(wait_sec),
            "expected_sec": int(expected),
            "questions_current": current,
            "questions_target": 140,
        })

    return {
        "max_concurrent": _MAX_CONCURRENT_QA_JOBS,
        "running_count": len(running_out),
        "queued_count": len(queued_out),
        "avg_by_kind": {k: int(v) for k, v in avg_by_kind.items()},
        "running": running_out,
        "queued": queued_out,
    }


@router.get("/jobs")
async def qa_jobs(_: dict = Depends(get_admin_user), limit: int = Query(30, ge=1, le=100)) -> list[dict]:
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
