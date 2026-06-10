"""Promo router: user redeem + admin CRUD."""
import secrets
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from core import db, get_current_user, get_admin_user, LIFETIME_DAYS, PromoCreate, PromoRedeem

router = APIRouter(tags=["promo"])


def _promo_to_public(p: dict) -> dict:
    return {"id": str(p["_id"]), "code": p["code"], "label": p.get("label") or "",
            "duration_days": p["duration_days"], "max_uses": p.get("max_uses"),
            "used_count": p.get("used_count", 0), "redeemed_by": p.get("redeemed_by", []),
            "expires_at": p.get("expires_at"), "active": p.get("active", True),
            "created_at": p.get("created_at"), "is_lifetime": p["duration_days"] >= LIFETIME_DAYS}


@router.post("/promo/redeem")
async def redeem_promo(body: PromoRedeem, user: dict = Depends(get_current_user)):
    code = body.code.strip().upper()
    promo = await db.promo_codes.find_one({"code": code})
    if not promo or not promo.get("active", True):
        raise HTTPException(status_code=404, detail="Code invalide ou expiré")
    if promo.get("expires_at"):
        try:
            exp_dt = datetime.fromisoformat(promo["expires_at"])
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if exp_dt < datetime.now(timezone.utc):
                raise HTTPException(status_code=410, detail="Ce code a expiré")
        except HTTPException:
            raise
        except Exception:
            pass
    used = promo.get("used_count", 0)
    if promo.get("max_uses") is not None and used >= promo["max_uses"]:
        raise HTTPException(status_code=410, detail="Ce code a atteint sa limite d'utilisations")
    redeemed_by = promo.get("redeemed_by", [])
    user_id_str = str(user["_id"])
    if user_id_str in redeemed_by:
        raise HTTPException(status_code=400, detail="Vous avez déjà utilisé ce code")
    days = int(promo["duration_days"])
    is_lifetime = days >= LIFETIME_DAYS
    expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    await db.users.update_one({"_id": ObjectId(user_id_str)},
                              {"$set": {"plan": "premium", "plan_expires_at": expires}})
    await db.promo_codes.update_one({"_id": promo["_id"]},
                                     {"$inc": {"used_count": 1}, "$push": {"redeemed_by": user_id_str}})
    return {"ok": True, "plan": "premium", "plan_expires_at": expires,
            "is_lifetime": is_lifetime, "duration_days": days, "label": promo.get("label") or ""}


@router.post("/admin/promo")
async def admin_create_promo(body: PromoCreate, admin: dict = Depends(get_admin_user)):
    code = (body.code or secrets.token_urlsafe(6)).strip().upper().replace(" ", "")
    if not code or len(code) < 2:
        raise HTTPException(status_code=400, detail="Code invalide")
    if await db.promo_codes.find_one({"code": code}):
        raise HTTPException(status_code=400, detail="Ce code existe déjà")
    doc = {"code": code, "label": (body.label or "").strip() or None,
           "duration_days": int(body.duration_days), "max_uses": body.max_uses,
           "expires_at": body.expires_at, "used_count": 0, "redeemed_by": [],
           "active": True, "created_at": datetime.now(timezone.utc).isoformat(),
           "created_by": str(admin["_id"])}
    result = await db.promo_codes.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _promo_to_public(doc)


@router.get("/admin/promo")
async def admin_list_promo(admin: dict = Depends(get_admin_user)):
    rows = await db.promo_codes.find().sort("created_at", -1).to_list(500)
    return [_promo_to_public(r) for r in rows]


@router.patch("/admin/promo/{promo_id}")
async def admin_toggle_promo(promo_id: str, admin: dict = Depends(get_admin_user)):
    try:
        oid = ObjectId(promo_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID invalide")
    promo = await db.promo_codes.find_one({"_id": oid})
    if not promo:
        raise HTTPException(status_code=404, detail="Code introuvable")
    new_active = not promo.get("active", True)
    await db.promo_codes.update_one({"_id": oid}, {"$set": {"active": new_active}})
    promo["active"] = new_active
    return _promo_to_public(promo)


@router.delete("/admin/promo/{promo_id}")
async def admin_delete_promo(promo_id: str, admin: dict = Depends(get_admin_user)):
    try:
        oid = ObjectId(promo_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID invalide")
    result = await db.promo_codes.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Code introuvable")
    return {"ok": True}
