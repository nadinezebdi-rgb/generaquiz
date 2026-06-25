"""Question reporting & admin review.

Any authenticated user can report a question they find factually wrong or ambiguous.
Reports are aggregated in MongoDB. Admins review them via /api/admin/reports and
can either delete the question (frees a slot for Mistral to regenerate at 03:00 Paris)
or dismiss the report.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import db, logger, get_current_user, get_admin_user

router = APIRouter(tags=["reports"])

ALLOWED_REASONS = {"factually_wrong", "ambiguous", "inappropriate", "duplicate", "other"}


class ReportRequest(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=80)
    reason: str = Field(..., min_length=2, max_length=40)
    comment: Optional[str] = Field(None, max_length=500)


class ResolveRequest(BaseModel):
    action: str = Field(..., pattern="^(delete|dismiss)$")


@router.post("/quiz/report")
async def report_question(body: ReportRequest, user: dict = Depends(get_current_user)):
    if body.reason not in ALLOWED_REASONS:
        raise HTTPException(status_code=400, detail=f"Raison invalide : {body.reason}")

    # Verify the question exists
    q = await db.questions.find_one({"id": body.question_id}, {"_id": 0, "id": 1, "category_id": 1, "question": 1})
    if not q:
        raise HTTPException(status_code=404, detail="Question introuvable")

    # 1 report per user per question per 24h (anti-spam / dedup)
    existing = await db.question_reports.find_one({
        "user_id": str(user["_id"]),
        "question_id": body.question_id,
        "status": "pending",
    })
    if existing:
        return {"ok": True, "already_reported": True, "report_id": existing.get("id")}

    doc = {
        "user_id": str(user["_id"]),
        "user_name": user.get("name") or user.get("email", "").split("@")[0],
        "question_id": body.question_id,
        "category_id": q["category_id"],
        "question_text": q["question"],
        "reason": body.reason,
        "comment": (body.comment or "").strip()[:500],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.question_reports.insert_one(doc)
    logger.info(f"[report] new {body.reason} on {body.question_id} by {user.get('email')}")
    return {"ok": True, "report_id": str(result.inserted_id)}


@router.get("/admin/reports")
async def list_reports(status: str = "pending", user: dict = Depends(get_admin_user)):
    """List all reports (default: pending). Aggregated per question for the admin UI."""
    if status not in ("pending", "resolved", "all"):
        raise HTTPException(status_code=400, detail="status doit être pending, resolved ou all")
    match: dict = {} if status == "all" else {"status": status}
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$question_id",
            "count": {"$sum": 1},
            "reasons": {"$push": "$reason"},
            "latest": {"$max": "$created_at"},
            "question_text": {"$first": "$question_text"},
            "category_id": {"$first": "$category_id"},
            "comments": {"$push": "$comment"},
        }},
        {"$sort": {"count": -1, "latest": -1}},
        {"$limit": 200},
    ]
    items = []
    async for grouped in db.question_reports.aggregate(pipeline):
        # Pull the full current question doc to show options + correct answer
        q = await db.questions.find_one({"id": grouped["_id"]}, {"_id": 0})
        items.append({
            "question_id": grouped["_id"],
            "category_id": grouped["category_id"],
            "question_text": grouped["question_text"],
            "report_count": grouped["count"],
            "reasons": grouped["reasons"],
            "comments": [c for c in grouped["comments"] if c],
            "latest_at": grouped["latest"],
            "question": q,  # may be None if already deleted
        })
    return {"status": status, "items": items, "count": len(items)}


@router.post("/admin/reports/{question_id}/resolve")
async def resolve_report(question_id: str, body: ResolveRequest, user: dict = Depends(get_admin_user)):
    """Resolve all pending reports on a question.

    - action=delete : remove the question from MongoDB. Mistral regenerates the pool tonight at 03:00 Paris.
    - action=dismiss : mark all pending reports as resolved without touching the question.
    """
    if body.action == "delete":
        del_res = await db.questions.delete_one({"id": question_id})
        if del_res.deleted_count == 0:
            logger.warning(f"[report] tried to delete missing question {question_id}")
    await db.question_reports.update_many(
        {"question_id": question_id, "status": "pending"},
        {"$set": {
            "status": "resolved",
            "resolved_action": body.action,
            "resolved_by": str(user["_id"]),
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"ok": True, "action": body.action, "question_id": question_id}
