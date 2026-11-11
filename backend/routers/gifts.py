"""Offrir GénéraQuiz : cartes cadeau (Famille / Solo), promo saisonnière, activation, admin."""
import re
import secrets
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from pymongo.errors import DuplicateKeyError

from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

from core import (db, logger, STRIPE_API_KEY, FRONTEND_URL, get_current_user, get_admin_user,
                  record_audit, rate_limit, is_premium_active)
from gift_card_pdf import build_gift_pdf

router = APIRouter(tags=["gifts"])

PARIS = ZoneInfo("Europe/Paris")
PROMO_KEY = "gift_promo"
DEFAULT_PROMO = {"enabled": False, "title": "Carte cadeau de Noël", "starts_on": "2026-12-01",
                 "ends_on": "2026-12-24", "famille_regular_price": 79.0, "famille_promo_price": 69.0}
SOLO_PRICE = 49.0
OFFERS = {"famille": {"tier": "famille_v2", "label": "Offre Famille — 1 an", "package_id": "gift_famille"},
          "solo": {"tier": "solo", "label": "Offre Solo — 1 an", "package_id": "gift_solo"}}
TIER_RANK = {"solo": 1, "club": 1, "famille": 2, "famille_v2": 2, "premium": 3, "heritage": 3}
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_RE = re.compile(r"^GQ-[A-Z0-9]{4}-[A-Z0-9]{4}$")


def _clean(v: Optional[str]) -> Optional[str]:
    v = (v or "").strip()
    return v or None


def normalize_code(raw: str) -> str:
    s = re.sub(r"[^A-Z0-9]", "", (raw or "").upper())
    if s.startswith("GQ"):
        s = s[2:]
    return f"GQ-{s[:4]}-{s[4:8]}" if len(s) == 8 else ""


def _new_code() -> str:
    pick = lambda: "".join(secrets.choice(CODE_ALPHABET) for _ in range(4))  # noqa: E731
    first = pick()
    while first.startswith("GQ"):
        first = pick()
    return f"GQ-{first}-{pick()}"


async def get_promo_settings() -> dict:
    doc = await db.site_settings.find_one({"key": PROMO_KEY}, {"_id": 0, "value": 1}) or {}
    return {**DEFAULT_PROMO, **(doc.get("value") or {})}


def promo_is_active(p: dict) -> bool:
    today = datetime.now(PARIS).date().isoformat()
    return bool(p["enabled"]) and p["starts_on"] <= today <= p["ends_on"]


async def current_offers() -> dict:
    p = await get_promo_settings()
    active = promo_is_active(p)
    famille_price = p["famille_promo_price"] if active else p["famille_regular_price"]
    return {
        "promo": {"active": active, "title": p["title"], "ends_on": p["ends_on"]},
        "offers": [
            {"id": "famille", "label": OFFERS["famille"]["label"], "price": famille_price,
             "regular_price": p["famille_regular_price"] if active else None},
            {"id": "solo", "label": OFFERS["solo"]["label"], "price": SOLO_PRICE, "regular_price": None},
        ],
    }


def _gift_public(g: dict) -> dict:
    return {"code": g["code"], "offer": g["offer"], "offer_label": OFFERS[g["offer"]]["label"],
            "recipient_name": g.get("recipient_name"), "buyer_name": g.get("buyer_name"),
            "message": g.get("message"), "status": g["status"], "theme": g.get("theme", "classic")}


def _pdf_url(g: dict) -> str:
    return f"/api/gifts/{g['code']}/carte.pdf?k={g['pdf_key']}"


async def _insert_gift(fields: dict) -> dict:
    for _ in range(6):
        doc = {**fields, "code": _new_code(), "pdf_key": secrets.token_urlsafe(16), "status": "active",
               "created_at": datetime.now(timezone.utc).isoformat()}
        try:
            await db.gift_codes.insert_one(doc)
            return doc
        except DuplicateKeyError as e:
            if "session_id" in str(e):
                return await db.gift_codes.find_one({"session_id": fields["session_id"]})
    raise HTTPException(status_code=500, detail="Impossible de générer un code cadeau")


async def fulfill_gift_transaction(tx: dict) -> dict:
    """Crée le code cadeau d'une transaction payée (idempotent : un code par session Stripe)."""
    existing = await db.gift_codes.find_one({"session_id": tx["session_id"]})
    if existing:
        return existing
    d = tx.get("gift") or {}
    return await _insert_gift({
        "offer": d["offer"], "tier": OFFERS[d["offer"]]["tier"], "amount": tx["amount"],
        "theme": d.get("theme", "classic"), "recipient_name": d.get("recipient_name"),
        "buyer_name": d.get("buyer_name"), "buyer_email": tx.get("user_email"),
        "message": d.get("message"), "source": "stripe", "session_id": tx["session_id"],
    })


# ------------------------------------------------------------------ public
class GiftCheckout(BaseModel):
    offer: Literal["famille", "solo"]
    recipient_name: str = Field(..., max_length=40)
    buyer_name: str = Field(..., max_length=40)
    buyer_email: EmailStr
    message: Optional[str] = Field(None, max_length=240)
    origin_url: Optional[str] = Field(None, max_length=300)

    @field_validator("recipient_name", "buyer_name")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Champ obligatoire")
        return v.strip()


@router.get("/gifts/offers")
async def gift_offers() -> dict:
    return await current_offers()


@router.post("/gifts/checkout", dependencies=[Depends(rate_limit("gift_checkout", 10, 60))])
async def gift_checkout(body: GiftCheckout, request: Request) -> dict:
    data = await current_offers()
    offer = next(o for o in data["offers"] if o["id"] == body.offer)
    theme = "noel" if data["promo"]["active"] else "classic"
    origin = FRONTEND_URL.rstrip("/")
    webhook_url = f"{str(request.base_url).rstrip('/')}/api/webhook/stripe"
    stripe = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    package_id = OFFERS[body.offer]["package_id"]
    session = await stripe.create_checkout_session(CheckoutSessionRequest(
        amount=float(offer["price"]), currency="eur",
        success_url=f"{origin}/offrir/merci?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/offrir",
        metadata={"package_id": package_id, "user_email": body.buyer_email, "gift_offer": body.offer},
    ))
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": None, "user_email": body.buyer_email,
        "package_id": package_id, "amount": float(offer["price"]), "currency": "eur",
        "metadata": {"package_id": package_id},
        "gift": {"offer": body.offer, "theme": theme, "recipient_name": body.recipient_name,
                 "buyer_name": body.buyer_name, "message": _clean(body.message)},
        "payment_status": "initiated", "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.session_id}


@router.get("/gifts/order/{session_id}")
async def gift_order_status(session_id: str, request: Request) -> dict:
    tx = await db.payment_transactions.find_one({"session_id": session_id, "gift": {"$exists": True}})
    if not tx:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if tx["payment_status"] != "paid":
        webhook_url = f"{str(request.base_url).rstrip('/')}/api/webhook/stripe"
        st = await StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url).get_checkout_status(session_id)
        await db.payment_transactions.update_one({"session_id": session_id},
                                                  {"$set": {"payment_status": st.payment_status, "status": st.status}})
        if st.payment_status != "paid":
            return {"payment_status": st.payment_status, "status": st.status}
    g = await fulfill_gift_transaction(tx)
    return {"payment_status": "paid", "status": "complete", "gift": _gift_public(g), "pdf_url": _pdf_url(g)}


@router.get("/gifts/code/{code}", dependencies=[Depends(rate_limit("gift_lookup", 20, 60))])
async def gift_lookup(code: str) -> dict:
    g = await db.gift_codes.find_one({"code": normalize_code(code)})
    if not g or g["status"] == "cancelled":
        raise HTTPException(status_code=404, detail="Ce code cadeau est introuvable. Vérifiez les lettres et chiffres.")
    return _gift_public(g)


@router.get("/gifts/{code}/carte.pdf")
async def gift_pdf(code: str, k: str) -> Response:
    g = await db.gift_codes.find_one({"code": normalize_code(code)})
    if not g or g["status"] == "cancelled" or not secrets.compare_digest(g["pdf_key"], k):
        raise HTTPException(status_code=404, detail="Carte introuvable")
    return _pdf_response(g)


def _pdf_response(g: dict) -> Response:
    pdf = build_gift_pdf(g, f"{FRONTEND_URL}/activer?code={g['code']}")
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="carte-cadeau-{g["code"]}.pdf"'})


class GiftRedeem(BaseModel):
    code: str = Field(..., min_length=4, max_length=20)


@router.post("/gifts/redeem", dependencies=[Depends(rate_limit("gift_redeem", 10, 60))])
async def gift_redeem(body: GiftRedeem, user: dict = Depends(get_current_user)) -> dict:
    code = normalize_code(body.code)
    now = datetime.now(timezone.utc)
    g = await db.gift_codes.find_one_and_update(
        {"code": code, "status": "active"},
        {"$set": {"status": "redeemed", "redeemed_at": now.isoformat(), "redeemed_by": str(user["_id"]),
                  "redeemed_by_email": user["email"]}})
    if not g:
        exists = await db.gift_codes.find_one({"code": code}, {"status": 1})
        if exists and exists["status"] == "redeemed":
            raise HTTPException(status_code=409, detail="Ce code cadeau a déjà été activé.")
        raise HTTPException(status_code=404, detail="Ce code cadeau est introuvable. Vérifiez les lettres et chiffres.")
    base = now
    tier = g["tier"]
    keep_lifetime = is_premium_active(user) and not user.get("plan_expires_at")
    if is_premium_active(user):
        try:
            cur = datetime.fromisoformat(user["plan_expires_at"])
            base = max(now, cur if cur.tzinfo else cur.replace(tzinfo=timezone.utc))
        except (KeyError, TypeError, ValueError):
            pass
        if TIER_RANK.get(user.get("plan_tier"), 0) > TIER_RANK[tier]:
            tier = user["plan_tier"]
    expires = None if keep_lifetime else (base + timedelta(days=365)).isoformat()
    await db.users.update_one({"_id": user["_id"]}, {"$set": {
        "plan": "premium", "plan_tier": tier, "plan_period": user.get("plan_period") if keep_lifetime else "yearly",
        "plan_expires_at": expires}})
    await db.gift_codes.update_one({"_id": g["_id"]}, {"$set": {"plan_expires_at": expires}})
    return {"ok": True, "offer": g["offer"], "offer_label": OFFERS[g["offer"]]["label"],
            "plan_tier": tier, "plan_expires_at": expires}


# ------------------------------------------------------------------ admin
class AdminGiftCreate(BaseModel):
    offer: Literal["famille", "solo"]
    recipient_name: Optional[str] = Field(None, max_length=40)
    buyer_name: Optional[str] = Field(None, max_length=40)
    message: Optional[str] = Field(None, max_length=240)
    theme: Literal["noel", "classic"] = "classic"


class PromoSettings(BaseModel):
    enabled: bool
    title: str = Field(..., min_length=3, max_length=60)
    starts_on: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    ends_on: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    famille_regular_price: float = Field(..., gt=0, le=1000)
    famille_promo_price: float = Field(..., gt=0, le=1000)


def _gift_admin(g: dict) -> dict:
    return {**_gift_public(g), "id": str(g["_id"]), "amount": g.get("amount", 0), "source": g.get("source"),
            "buyer_email": g.get("buyer_email"), "created_at": g.get("created_at"),
            "redeemed_at": g.get("redeemed_at"), "redeemed_by_email": g.get("redeemed_by_email"),
            "plan_expires_at": g.get("plan_expires_at"), "pdf_url": _pdf_url(g)}


@router.get("/admin/gifts")
async def admin_list_gifts(admin: dict = Depends(get_admin_user)) -> dict:
    rows = await db.gift_codes.find().sort("created_at", -1).to_list(1000)
    paid = [r for r in rows if r.get("source") == "stripe"]
    return {"gifts": [_gift_admin(r) for r in rows],
            "stats": {"sold": len(paid), "revenue": round(sum(r.get("amount", 0) for r in paid), 2),
                      "redeemed": sum(1 for r in rows if r["status"] == "redeemed"),
                      "pending": sum(1 for r in rows if r["status"] == "active")}}


@router.post("/admin/gifts")
async def admin_create_gift(body: AdminGiftCreate, admin: dict = Depends(get_admin_user)) -> dict:
    g = await _insert_gift({"offer": body.offer, "tier": OFFERS[body.offer]["tier"], "amount": 0,
                            "theme": body.theme, "recipient_name": _clean(body.recipient_name),
                            "buyer_name": _clean(body.buyer_name), "message": _clean(body.message),
                            "source": "admin", "session_id": f"admin-{ObjectId()}",
                            "created_by": str(admin["_id"])})
    await record_audit(admin, action="gift.create", target_type="gift", target_label=g["code"],
                       meta={"offer": body.offer})
    return _gift_admin(g)


@router.patch("/admin/gifts/{code}/cancel")
async def admin_cancel_gift(code: str, admin: dict = Depends(get_admin_user)) -> dict:
    g = await db.gift_codes.find_one_and_update({"code": normalize_code(code), "status": "active"},
                                                {"$set": {"status": "cancelled"}}, return_document=True)
    if not g:
        raise HTTPException(status_code=400, detail="Seul un code non activé peut être annulé")
    await record_audit(admin, action="gift.cancel", target_type="gift", target_label=g["code"])
    return _gift_admin(g)


@router.get("/admin/site-settings/gift-promo")
async def admin_get_promo(admin: dict = Depends(get_admin_user)) -> dict:
    p = await get_promo_settings()
    return {**p, "active_now": promo_is_active(p)}


@router.put("/admin/site-settings/gift-promo")
async def admin_set_promo(body: PromoSettings, admin: dict = Depends(get_admin_user)) -> dict:
    if body.starts_on > body.ends_on:
        raise HTTPException(status_code=400, detail="La date de début doit précéder la date de fin")
    if body.famille_promo_price >= body.famille_regular_price:
        raise HTTPException(status_code=400, detail="Le prix promo doit être inférieur au prix normal")
    value = body.model_dump()
    await db.site_settings.update_one({"key": PROMO_KEY}, {"$set": {"key": PROMO_KEY, "value": value}}, upsert=True)
    await record_audit(admin, action="site.gift_promo", target_type="system", meta=value)
    return {**value, "active_now": promo_is_active(value)}


async def ensure_gift_indexes() -> None:
    await db.gift_codes.create_index("code", unique=True)
    await db.gift_codes.create_index("session_id", unique=True)
