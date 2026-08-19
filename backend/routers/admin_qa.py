"""Admin QA — pilotage du fact-check et modération des questions IA.

Endpoints (rôle admin requis) :
    GET  /admin/qa/summary              : résumé par catégorie (verified/flagged/unchecked)
    GET  /admin/qa/questions            : liste paginée des questions avec filtres
    POST /admin/qa/{id}/approve         : force une question flagged → verified
    POST /admin/qa/{id}/flag            : force une question → flagged (retire du tirage)
    POST /admin/qa/{id}/apply-correction: applique la correction proposée par le fact-check
    DELETE /admin/qa/{id}               : supprime la question de la DB
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core import db, get_admin_user

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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """Liste paginée des questions avec leur statut fact-check.

    Utile pour la revue admin : par défaut on liste les `flagged` (à modérer).
    """
    q: dict = {}
    if category_id:
        q["category_id"] = category_id
    if quality == "verified":
        q["quality"] = "verified"
    elif quality == "flagged":
        q["quality"] = "flagged"
    elif quality == "unchecked":
        q["quality"] = {"$exists": False}
    # "all" → pas de filtre quality

    total = await db.questions.count_documents(q)
    docs = await db.questions.find(q, {"_id": 0}).sort([("fact_check.confidence", 1), ("id", 1)]).skip(offset).limit(limit).to_list(limit)
    return {"total": total, "limit": limit, "offset": offset, "questions": docs}


class ApproveBody(BaseModel):
    reason: str = Field("", max_length=300)


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
async def qa_delete(qid: str, _: dict = Depends(get_admin_user)) -> dict:
    r = await db.questions.delete_one({"id": qid})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Question introuvable")
    return {"ok": True}
