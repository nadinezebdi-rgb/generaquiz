"""Admin — journal d'audit lecture seule.

Endpoints :
    GET /admin/audit                : liste paginée du journal (superadmin uniquement)
    GET /admin/audit/actions        : liste distinct des actions (pour filtre UI)

Le remplissage du journal est fait par le helper `record_audit()` dans `core.py`,
appelé depuis chaque endpoint sensible.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query

from core import db, get_superadmin_user

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


@router.get("")
async def list_audit(
    action: Optional[str] = Query(None, description="Filtre par action exacte"),
    admin_email: Optional[str] = Query(None, description="Filtre par email admin"),
    q: Optional[str] = Query(None, description="Recherche libre (target_label, action, admin_email)"),
    limit: int = Query(100, ge=1, le=500),
    skip: int = Query(0, ge=0),
    _: dict = Depends(get_superadmin_user),
) -> dict:
    query: dict = {}
    if action:
        query["action"] = action
    if admin_email:
        query["admin_email"] = admin_email
    if q:
        query["$or"] = [
            {"target_label": {"$regex": q, "$options": "i"}},
            {"action": {"$regex": q, "$options": "i"}},
            {"admin_email": {"$regex": q, "$options": "i"}},
        ]

    total = await db.admin_audit_log.count_documents(query)
    cursor = db.admin_audit_log.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    events = await cursor.to_list(limit)
    return {"total": total, "skip": skip, "limit": limit, "events": events}


@router.get("/actions")
async def list_actions(_: dict = Depends(get_superadmin_user)) -> list[str]:
    return sorted(await db.admin_audit_log.distinct("action"))
