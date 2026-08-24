"""Admin — gestion des rôles utilisateurs.

Endpoints :
    GET  /admin/users                     : liste paginée + recherche (rôle admin ou superadmin)
    POST /admin/users/{user_id}/role      : promouvoir/rétrograder (superadmin uniquement)

Règles strictes :
    - Impossible de se rétrograder soi-même.
    - Impossible de retirer/changer le rôle d'un superadmin (garantit un point d'entrée unique).
    - Impossible de créer un second superadmin depuis l'UI — le superadmin est
      exclusivement celui défini via ADMIN_EMAIL au seed.
    - Seuls les rôles "admin" et "user" sont assignables via cet endpoint.
"""
from typing import Literal, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core import db, get_admin_user, get_superadmin_user, record_audit

router = APIRouter(prefix="/admin/users", tags=["admin-users"])

_PUBLIC_FIELDS = {
    "_id": 0, "id": {"$toString": "$_id"},
    "email": 1, "name": 1, "role": 1, "plan": 1, "plan_tier": 1, "plan_period": 1,
    "created_at": 1, "plan_expires_at": 1,
}


@router.get("")
async def list_users(
    q: Optional[str] = Query(None, description="Recherche email ou nom (contient)"),
    role: Optional[str] = Query(None, description="Filtre par rôle exact"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    _: dict = Depends(get_admin_user),
) -> dict:
    query: dict = {}
    if q:
        query["$or"] = [
            {"email": {"$regex": q, "$options": "i"}},
            {"name": {"$regex": q, "$options": "i"}},
        ]
    if role:
        query["role"] = role

    total = await db.users.count_documents(query)
    cursor = db.users.find(query, {"password_hash": 0}).sort("created_at", -1).skip(skip).limit(limit)
    users = []
    async for u in cursor:
        users.append({
            "id": str(u["_id"]),
            "email": u.get("email"),
            "name": u.get("name"),
            "role": u.get("role") or "user",
            "plan": u.get("plan"),
            "plan_tier": u.get("plan_tier"),
            "plan_period": u.get("plan_period"),
            "created_at": u.get("created_at"),
            "plan_expires_at": u.get("plan_expires_at"),
        })
    return {"total": total, "skip": skip, "limit": limit, "users": users}


class RoleChange(BaseModel):
    role: Literal["admin", "user"]


@router.post("/{user_id}/role")
async def change_role(user_id: str, body: RoleChange, admin: dict = Depends(get_superadmin_user)) -> dict:
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID utilisateur invalide")

    target = await db.users.find_one({"_id": oid})
    if not target:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    # Garde-fou 1 : impossible de modifier son propre rôle depuis cette route.
    if str(admin["_id"]) == str(target["_id"]):
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas modifier votre propre rôle")

    # Garde-fou 2 : impossible de rétrograder un superadmin — garantit un point
    # d'entrée unique pour la gouvernance des rôles.
    if target.get("role") == "superadmin":
        raise HTTPException(status_code=403, detail="Impossible de modifier le rôle d'un super-administrateur")

    # Garde-fou 3 : cet endpoint n'accepte que admin/user (pas superadmin).
    # Le typage Literal protège déjà, mais on double-check.
    if body.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Rôle non assignable via cette interface")

    previous_role = target.get("role") or "user"
    if previous_role == body.role:
        return {"ok": True, "unchanged": True, "user_id": user_id, "role": body.role}

    await db.users.update_one({"_id": oid}, {"$set": {"role": body.role}})

    await record_audit(
        admin,
        action="user.role_change",
        target_type="user",
        target_id=user_id,
        target_label=target.get("email"),
        before={"role": previous_role},
        after={"role": body.role},
    )

    return {"ok": True, "user_id": user_id, "role": body.role, "previous_role": previous_role}
