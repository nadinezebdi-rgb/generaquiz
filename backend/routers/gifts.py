"""Offrir GénéraQuiz : cartes cadeau (Famille / Solo), promo saisonnière, activation, admin."""
import asyncio
import base64
import html
import hashlib
import hmac
import io
import re
import secrets
from datetime import date as Date, datetime, time as Time, timezone, timedelta
from decimal import Decimal
from typing import Literal, Optional
from zoneinfo import ZoneInfo

import stripe
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from cryptography.fernet import Fernet
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from pymongo.errors import DuplicateKeyError, OperationFailure
from pymongo import ReturnDocument
import resend

from core import (
    GIFT_CODE_ENCRYPTION_KEY, GIFT_STRIPE_LIVE_PRODUCT_ID, GIFT_STRIPE_LIVE_PRICE_ID,
    GIFT_STRIPE_LIVE_SECRET_KEY, GIFT_STRIPE_LIVE_WEBHOOK_SECRET, GIFT_STRIPE_MODE,
    GIFT_STRIPE_TEST_PRODUCT_ID, GIFT_STRIPE_TEST_PRICE_ID, GIFT_STRIPE_TEST_SECRET_KEY,
    GIFT_STRIPE_TEST_WEBHOOK_SECRET, FRONTEND_URL, STRIPE_WEBHOOK_SECRET, client, db,
    JWT_SECRET, STRIPE_API_KEY,
    RESEND_API_KEY, SENDER_EMAIL, get_admin_user, get_current_user, is_premium_active,
    logger, rate_limit, record_audit,
)
from gift_card_pdf import build_gift_pdf
from routers.family import family_subscription_fields

router = APIRouter(tags=["gifts"])

PARIS = ZoneInfo("Europe/Paris")
PROMO_KEY = "gift_promo"
DEFAULT_PROMO = {"enabled": False, "title": "Carte cadeau de Noël", "starts_on": "2026-12-01",
                 "ends_on": "2026-12-24", "famille_regular_price": 79.0, "famille_promo_price": 69.0}
SOLO_PRICE = 49.0
OFFERS = {"famille": {"tier": "famille_v2", "label": "Offre Famille — 1 an", "package_id": "gift_famille"},
          "solo": {"tier": "solo", "label": "Offre Solo — 1 an", "package_id": "gift_solo"},
          "noel": {"tier": "solo", "label": "Carte cadeau de Noël — 1 accès personnel", "package_id": "gift_solo"}}
NOEL_TIER = "solo"
TIER_RANK = {"solo": 1, "club": 1, "famille": 2, "famille_v2": 2, "premium": 3, "heritage": 3}
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
SALE_CUTOFF = datetime(2026, 12, 24, 23, 0, tzinfo=timezone.utc)
PDF_BUCKET = "gift_cards"


def normalize_code(raw: str) -> str:
    s = re.sub(r"[^A-Z0-9]", "", (raw or "").upper())
    if s.startswith("GQ"):
        s = s[2:]
    if len(s) == 8 and all(char in CODE_ALPHABET for char in s):
        return f"GQ-{s[:4]}-{s[4:]}"
    if len(s) == 32 and all(char in CODE_ALPHABET for char in s):
        return "GQ-" + "-".join(s[index:index + 8] for index in range(0, 32, 8))
    return ""


def _new_code() -> str:
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(32))
    return "GQ-" + "-".join(raw[index:index + 8] for index in range(0, 32, 8))


def _gift_encryption_key() -> str:
    """Clé dédiée si fournie, sinon dérivée de JWT_SECRET (stable par environnement)."""
    if GIFT_CODE_ENCRYPTION_KEY:
        return GIFT_CODE_ENCRYPTION_KEY
    return base64.urlsafe_b64encode(hashlib.sha256(b"gq-gift-codes-v1:" + JWT_SECRET.encode()).digest()).decode()


def _fernet() -> Fernet:
    try:
        return Fernet(_gift_encryption_key().encode())
    except Exception as exc:
        logger.error("Clé de chiffrement des cartes cadeau invalide")
        raise HTTPException(status_code=503, detail="Le service de cartes cadeau n'est pas configuré") from exc


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("ascii")).hexdigest()


def _clean(value: Optional[str]) -> Optional[str]:
    value = (value or "").strip()
    return value or None


def _reveal_code(gift: dict) -> str:
    if gift.get("code"):
        return gift["code"]
    if gift.get("code_encrypted"):
        return _fernet().decrypt(gift["code_encrypted"].encode()).decode("ascii")
    return ""


async def _find_gift_by_code(code: str) -> Optional[dict]:
    normalized = normalize_code(code)
    if not normalized:
        return None
    gift = await db.gift_codes.find_one({"code_hash": _hash_code(normalized)})
    if gift:
        return gift
    # Compatibility for codes issued before hashed storage was introduced.
    return await db.gift_codes.find_one({"code": normalized})


def _stripe_config(mode: Optional[str] = None, offer_id: Optional[str] = None) -> dict:
    selected = (mode or GIFT_STRIPE_MODE).lower()
    if selected == "test":
        key, webhook = GIFT_STRIPE_TEST_SECRET_KEY, GIFT_STRIPE_TEST_WEBHOOK_SECRET
        product_id, price_id = GIFT_STRIPE_TEST_PRODUCT_ID, GIFT_STRIPE_TEST_PRICE_ID
    elif selected == "live":
        key, webhook = GIFT_STRIPE_LIVE_SECRET_KEY, GIFT_STRIPE_LIVE_WEBHOOK_SECRET
        product_id, price_id = GIFT_STRIPE_LIVE_PRODUCT_ID, GIFT_STRIPE_LIVE_PRICE_ID
    else:
        raise HTTPException(status_code=503, detail="L'environnement de paiement cadeau est invalide")
    expected_prefix = "sk_test_" if selected == "test" else "sk_live_"
    if not key.startswith(expected_prefix) or not webhook.startswith("whsec_"):
        raise HTTPException(status_code=503, detail="Le paiement cadeau n'est pas configuré pour cet environnement")
    # Configured product/price IDs are the campaign's family SKU; solo has its own catalog entry.
    if offer_id != "famille":
        product_id, price_id = "", ""
    return {"mode": selected, "api_key": key, "webhook_secret": webhook,
            "product_id": product_id, "price_id": price_id}


def _stripe_create_catalog_entry(config: dict, offer_id: str, amount_cents: int, tier: str) -> dict:
    stripe.api_key = config["api_key"]
    product_id = config["product_id"]
    if product_id:
        product = stripe.Product.retrieve(product_id)
        if not product.get("active"):
            product = stripe.Product.modify(product_id, active=True)
    else:
        product = stripe.Product.create(
            name=f"GénéraQuiz — Carte cadeau {offer_id.title()}",
            description="Accès cadeau valable un an à partir de l'activation, paiement unique.",
            metadata={"gq_catalog": "gift_card_v1", "gq_offer": offer_id,
                      "gq_tier": tier, "gq_environment": config["mode"]},
            idempotency_key=f"gq-gift-product-v1-{config['mode']}-{offer_id}",
        )

    price_id = config["price_id"]
    price = stripe.Price.retrieve(price_id) if price_id else None
    if price and (price.get("unit_amount") != amount_cents or price.get("currency") != "eur"
                  or price.get("product") != product["id"] or price.get("type") != "one_time"):
        price = None
    if not price:
        price = stripe.Price.create(
            product=product["id"], currency="eur", unit_amount=amount_cents,
            metadata={"gq_catalog": "gift_card_v1", "gq_offer": offer_id,
                      "gq_environment": config["mode"]},
            idempotency_key=f"gq-gift-price-v1-{config['mode']}-{offer_id}-{amount_cents}",
        )
    return {"product_id": product["id"], "price_id": price["id"]}


def _native_stripe_configured() -> bool:
    try:
        _stripe_config()
        return True
    except HTTPException:
        return False


def _platform_checkout() -> StripeCheckout:
    """Paiement Stripe de la plateforme (le même que les abonnements)."""
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{FRONTEND_URL.rstrip('/')}/api/webhook/stripe")


async def _ensure_stripe_catalog_entry(offer_id: str, amount_cents: int, tier: str) -> dict:
    config = _stripe_config(offer_id=offer_id)
    cache_key = f"gift_stripe_catalog_{config['mode']}_{offer_id}_{amount_cents}"
    cached = await db.site_settings.find_one({"key": cache_key}, {"_id": 0, "value": 1})
    if cached and cached.get("value", {}).get("product_id"):
        return {**cached["value"], "mode": config["mode"]}
    catalog = await asyncio.to_thread(_stripe_create_catalog_entry, config, offer_id, amount_cents, tier)
    catalog.update({"offer": offer_id, "amount_cents": amount_cents, "currency": "eur", "mode": config["mode"]})
    await db.site_settings.update_one({"key": cache_key}, {"$set": {"key": cache_key, "value": catalog}}, upsert=True)
    return catalog


async def get_promo_settings() -> dict:
    doc = await db.site_settings.find_one({"key": PROMO_KEY}, {"_id": 0, "value": 1}) or {}
    return {**DEFAULT_PROMO, **(doc.get("value") or {})}


def promo_is_active(p: dict) -> bool:
    now = datetime.now(timezone.utc)
    today = now.astimezone(PARIS).date().isoformat()
    return bool(p["enabled"]) and p["starts_on"] <= today <= p["ends_on"] and now < SALE_CUTOFF


async def current_offers() -> dict:
    p = await get_promo_settings()
    active = promo_is_active(p)
    closed = datetime.now(timezone.utc) >= SALE_CUTOFF
    famille_price = p["famille_promo_price"] if active else p["famille_regular_price"]
    offers = [
        {"id": "famille", "label": OFFERS["famille"]["label"], "price": famille_price,
         "regular_price": p["famille_regular_price"] if active else None},
        {"id": "solo", "label": OFFERS["solo"]["label"], "price": SOLO_PRICE, "regular_price": None},
    ]
    if active:
        offers.insert(0, {"id": "noel", "label": p["title"], "price": famille_price,
                          "regular_price": p["famille_regular_price"]})
    return {
        "promo": {"active": active, "closed": closed, "title": p["title"], "ends_on": "2026-12-24"},
        "offers": offers,
    }


def _gift_public(g: dict) -> dict:
    status = {"active": "available", "redeemed": "activated", "cancelled": "revoked"}.get(g["status"], g["status"])
    label = "Carte cadeau de Noël — 1 accès personnel" if g.get("theme", "").startswith("noel_") else OFFERS[g["offer"]]["label"]
    return {"code": _reveal_code(g), "offer": g["offer"], "offer_label": label,
            "recipient_name": g.get("recipient_name"), "buyer_name": g.get("buyer_name"),
            "message": g.get("message"), "status": status, "theme": g.get("theme", "classic")}


def _pdf_url(g: dict) -> str:
    code = _reveal_code(g)
    return f"/api/gifts/{code}/carte.pdf?k={g['pdf_key']}"


def _download_token(order_id: str, ttl_seconds: int = 900) -> str:
    expires = int(datetime.now(timezone.utc).timestamp()) + ttl_seconds
    payload = f"{order_id}.{expires}".encode("ascii")
    signing_key = hashlib.sha256(GIFT_CODE_ENCRYPTION_KEY.encode()).digest()
    signature = hmac.new(signing_key, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"." + signature).decode().rstrip("=")


def _buyer_access_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _valid_download_token(token: str, order_id: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
        if len(raw) < 34 or raw[-33:-32] != b".":
            return False
        payload, signature = raw[:-33], raw[-32:]
        token_order, expires = payload.decode("ascii").rsplit(".", 1)
        expected = hmac.new(hashlib.sha256(GIFT_CODE_ENCRYPTION_KEY.encode()).digest(), payload,
                            hashlib.sha256).digest()
        return (token_order == order_id and int(expires) >= int(datetime.now(timezone.utc).timestamp())
                and hmac.compare_digest(signature, expected))
    except (ValueError, UnicodeDecodeError):
        return False


async def _ensure_gift_pdf(gift: dict) -> bool:
    if gift.get("pdf_file_id"):
        return True
    now = datetime.now(timezone.utc)
    generation_token = secrets.token_urlsafe(16)
    claimed = await db.gift_codes.find_one_and_update(
        {"_id": gift["_id"], "pdf_file_id": {"$exists": False}, "$or": [
            {"pdf_status": {"$ne": "generating"}}, {"pdf_lease_until": {"$lt": now}},
        ]},
        {"$set": {"pdf_status": "generating", "pdf_generation_token": generation_token,
                  "pdf_lease_until": now + timedelta(minutes=5)}},
        return_document=ReturnDocument.AFTER,
    )
    if not claimed:
        current = await db.gift_codes.find_one({"_id": gift["_id"]}, {"pdf_file_id": 1})
        return bool(current and current.get("pdf_file_id"))
    try:
        printable = {**claimed, "code": _reveal_code(claimed)}
        pdf = await asyncio.to_thread(
            build_gift_pdf, printable,
            f"{FRONTEND_URL.rstrip('/')}/activer?code={printable['code']}",
        )
        bucket = AsyncIOMotorGridFSBucket(db, bucket_name=PDF_BUCKET)
        file_id = await bucket.upload_from_stream(
            f"gift-{claimed['_id']}.pdf", pdf,
            metadata={"gift_id": str(claimed["_id"]), "content_type": "application/pdf"},
        )
        saved = await db.gift_codes.update_one(
            {"_id": claimed["_id"], "pdf_generation_token": generation_token,
             "pdf_file_id": {"$exists": False}},
            {"$set": {"pdf_file_id": file_id, "pdf_status": "ready", "pdf_created_at": datetime.now(timezone.utc)},
             "$unset": {"pdf_generation_token": "", "pdf_lease_until": ""}},
        )
        if not saved.modified_count:
            await bucket.delete(file_id)
        return bool(saved.modified_count)
    except Exception:
        logger.exception("Génération PDF cadeau échouée (gift=%s)", gift.get("_id"))
        await db.gift_codes.update_one(
            {"_id": gift["_id"], "pdf_generation_token": generation_token},
            {"$set": {"pdf_status": "failed", "pdf_last_attempt_at": datetime.now(timezone.utc)},
             "$unset": {"pdf_generation_token": "", "pdf_lease_until": ""}},
        )
        return False


async def retry_pending_gift_pdfs() -> None:
    cursor = db.gift_codes.find({"status": {"$in": ["available", "active"]},
                                 "pdf_file_id": {"$exists": False}}).limit(30)
    async for gift in cursor:
        await _ensure_gift_pdf(gift)


def _with_code(gift: dict, code: str) -> dict:
    """Document interne (jamais renvoyé tel quel à l'API) enrichi du code en clair."""
    out = dict(gift)
    out["code"] = code
    return out


async def _insert_gift(fields: dict) -> dict:
    for _ in range(6):
        code = _new_code()
        doc = {**fields, "code_hash": _hash_code(code), "code_encrypted": _fernet().encrypt(code.encode()).decode(),
               "code_last4": code[-4:], "pdf_key": secrets.token_urlsafe(24), "status": "available",
               "created_at": datetime.now(timezone.utc)}
        try:
            await db.gift_codes.insert_one(doc)
            return _with_code(doc, code)
        except DuplicateKeyError as e:
            if fields.get("order_id"):
                existing = await db.gift_codes.find_one({"order_id": fields["order_id"]})
                if existing:
                    return _with_code(existing, _reveal_code(existing))
            if fields.get("session_id") and "session_id" in str(e):
                existing = await db.gift_codes.find_one({"session_id": fields["session_id"]})
                if existing:
                    return _with_code(existing, _reveal_code(existing))
    raise HTTPException(status_code=500, detail="Impossible de générer un code cadeau")


async def fulfill_gift_transaction(tx: dict) -> dict:
    """Émet au plus un code après vérification serveur du paiement Stripe."""
    if tx.get("payment_status") != "paid" or tx.get("stripe_verified") is not True:
        raise HTTPException(status_code=409, detail="Le paiement n'est pas confirmé")
    existing = await db.gift_codes.find_one({"order_id": tx["_id"]})
    if existing:
        return {**existing, "code": _reveal_code(existing)}
    d = tx.get("gift") or {}
    return await _insert_gift({
        "order_id": tx["_id"], "offer": d["offer"], "tier": d.get("tier", OFFERS[d["offer"]]["tier"]),
        "product_id": tx.get("stripe_product_id"), "price_id": tx.get("stripe_price_id"),
        "amount": tx["amount"], "currency": tx["currency"],
        "theme": d.get("theme", "classic"), "recipient_name": d.get("recipient_name"),
        "buyer_name": d.get("buyer_name"), "buyer_email": d.get("buyer_email"),
        "message": d.get("message"), "source": "stripe", "session_id": tx["session_id"],
    })


# ------------------------------------------------------------------ public
class GiftCheckout(BaseModel):
    offer: Literal["famille", "solo", "noel"]
    theme: Literal["classic", "noel_femme", "noel_homme"] = "classic"
    recipient_name: str = Field(..., max_length=40)
    buyer_name: str = Field(..., max_length=40)
    buyer_full_name: str = Field(..., max_length=80)
    buyer_email: EmailStr
    message: Optional[str] = Field(None, max_length=240)
    delivery_method: Literal["self", "direct"] = "self"
    recipient_email: Optional[EmailStr] = None
    delivery_date: Optional[Date] = None
    origin_url: Optional[str] = Field(None, max_length=300)

    @field_validator("recipient_name", "buyer_name")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Champ obligatoire")
        return v.strip()

    @field_validator("buyer_full_name")
    @classmethod
    def _buyer_name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Champ obligatoire")
        return value.strip()

    @model_validator(mode="after")
    def _validate_delivery(self):
        if self.delivery_method == "direct":
            if not self.recipient_email or not self.delivery_date:
                raise ValueError("L’e-mail du bénéficiaire et la date d’envoi sont requis")
            scheduled = datetime.combine(self.delivery_date, Time(9), tzinfo=PARIS)
            if scheduled <= datetime.now(PARIS):
                raise ValueError("La date d’envoi doit être future")
        elif self.recipient_email or self.delivery_date:
            raise ValueError("Les coordonnées de remise directe ne s’appliquent qu’à l’envoi direct")
        return self


@router.get("/gifts/offers")
async def gift_offers() -> dict:
    return await current_offers()


@router.post("/gifts/checkout", dependencies=[Depends(rate_limit("gift_checkout", 10, 60))])
async def gift_checkout(body: GiftCheckout, request: Request) -> dict:
    data = await current_offers()
    if data["promo"]["closed"] and body.offer == "noel":
        raise HTTPException(status_code=410, detail="L'offre de Noël est terminée")
    offer = next((o for o in data["offers"] if o["id"] == body.offer), None)
    if not offer:
        raise HTTPException(status_code=410 if body.offer == "noel" else 400,
                            detail="L'offre de Noël est terminée" if body.offer == "noel" else "Offre invalide")
    is_christmas = data["promo"]["active"] and body.offer == "noel"
    if body.theme.startswith("noel_") and not is_christmas:
        raise HTTPException(status_code=400, detail="Le modèle Noël n'est plus disponible")
    theme = body.theme if is_christmas and body.theme.startswith("noel_") else ("noel_femme" if is_christmas else "classic")
    tier = NOEL_TIER if is_christmas else OFFERS[body.offer]["tier"]
    if is_christmas and datetime.now(timezone.utc) >= SALE_CUTOFF:
        raise HTTPException(status_code=410, detail="L'offre de Noël est terminée")
    _fernet()
    amount_cents = int((Decimal(str(offer["price"])) * 100).quantize(Decimal("1")))
    platform = not _native_stripe_configured()
    catalog = ({"mode": "platform", "product_id": None, "price_id": None} if platform
               else await _ensure_stripe_catalog_entry(body.offer, amount_cents, tier))
    mode = catalog["mode"]
    order_id = ObjectId()
    buyer_access_token = secrets.token_urlsafe(32)
    package_id = OFFERS[body.offer]["package_id"]
    now = datetime.now(timezone.utc)
    delivery_at = (datetime.combine(body.delivery_date, Time(9), tzinfo=PARIS).astimezone(timezone.utc)
                   if body.delivery_method == "direct" else None)
    transaction = {
        "_id": order_id, "session_id": f"pending:{order_id}", "user_id": None,
        "user_email": str(body.buyer_email), "package_id": package_id,
        "amount": amount_cents / 100, "amount_cents": amount_cents, "currency": "eur",
        "stripe_mode": mode, "stripe_product_id": catalog["product_id"],
        "stripe_price_id": catalog["price_id"], "stripe_verified": False,
        "buyer_access_hash": _buyer_access_hash(buyer_access_token),
        "metadata": {"package_id": package_id, "gift_order_id": str(order_id)},
        "gift": {"offer": body.offer, "tier": tier, "theme": theme,
                 "recipient_name": body.recipient_name.strip(), "buyer_name": body.buyer_name.strip(),
                 "buyer_full_name": body.buyer_full_name.strip(),
                 "buyer_email": str(body.buyer_email).lower(), "message": _clean(body.message),
                 "delivery_method": body.delivery_method,
                 "recipient_email": str(body.recipient_email).lower() if body.recipient_email else None,
                 "delivery_at": delivery_at,
                 "is_christmas": is_christmas},
        "payment_status": "initiated", "status": "creating", "gift_delivery_status": "awaiting_payment",
        "created_at": now,
    }
    await db.payment_transactions.insert_one(transaction)

    origin = FRONTEND_URL.rstrip("/")
    if platform:
        try:
            ps = await _platform_checkout().create_checkout_session(CheckoutSessionRequest(
                amount=amount_cents / 100, currency="eur",
                success_url=f"{origin}/offrir/merci?session_id={{CHECKOUT_SESSION_ID}}#access={buyer_access_token}",
                cancel_url=f"{origin}/offrir",
                metadata={"gift_order_id": str(order_id), "gift_offer": body.offer, "package_id": package_id},
            ))
        except Exception as exc:
            await db.payment_transactions.update_one({"_id": order_id}, {"$set": {"status": "checkout_error"}})
            logger.error("Création de session Stripe cadeau impossible (order=%s): %s", order_id, exc)
            raise HTTPException(status_code=503, detail="Impossible de démarrer le paiement") from exc
        await db.payment_transactions.update_one({"_id": order_id}, {"$set": {
            "session_id": ps.session_id, "status": "open", "checkout_url": ps.url}})
        return {"url": ps.url, "session_id": ps.session_id}
    config = _stripe_config(mode, body.offer)
    stripe.api_key = config["api_key"]
    try:
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            mode="payment",
            payment_method_types=["card"],
            line_items=[{"price": catalog["price_id"], "quantity": 1}],
            customer_email=str(body.buyer_email),
            client_reference_id=str(order_id),
            success_url=f"{origin}/offrir/merci?session_id={{CHECKOUT_SESSION_ID}}#access={buyer_access_token}",
            cancel_url=f"{origin}/offrir",
            metadata={"gift_order_id": str(order_id), "gift_offer": body.offer},
            payment_intent_data={"metadata": {"gift_order_id": str(order_id)}},
            idempotency_key=f"gq-gift-checkout-v1-{order_id}",
        )
    except Exception as exc:
        await db.payment_transactions.update_one({"_id": order_id}, {"$set": {"status": "checkout_error"}})
        logger.error("Création de session Stripe cadeau impossible (order=%s)", order_id)
        raise HTTPException(status_code=503, detail="Impossible de démarrer le paiement") from exc

    if is_christmas and datetime.now(timezone.utc) >= SALE_CUTOFF:
        try:
            await asyncio.to_thread(stripe.checkout.Session.expire, session["id"])
        finally:
            await db.payment_transactions.update_one({"_id": order_id}, {"$set": {"status": "expired"}})
        raise HTTPException(status_code=410, detail="L'offre de Noël est terminée")
    await db.payment_transactions.update_one({"_id": order_id}, {"$set": {
        "session_id": session["id"], "status": session.get("status", "open"),
        "checkout_url": session["url"], "stripe_session_created": session.get("created"),
    }})
    return {"url": session["url"], "session_id": session["id"]}


async def _retrieve_checkout_session(tx: dict) -> dict:
    config = _stripe_config(tx.get("stripe_mode"), tx.get("gift", {}).get("offer"))
    stripe.api_key = config["api_key"]
    return await asyncio.to_thread(
        stripe.checkout.Session.retrieve, tx["session_id"],
        expand=["line_items.data.price.product", "payment_intent.latest_charge"],
    )


def _stripe_object(value):
    return value.to_dict_recursive() if hasattr(value, "to_dict_recursive") else value


def _validate_paid_session(tx: dict, session) -> dict:
    session = _stripe_object(session)
    metadata = session.get("metadata") or {}
    line_items = (session.get("line_items") or {}).get("data") or []
    if (session.get("id") != tx.get("session_id") or session.get("mode") != "payment"
            or session.get("status") != "complete" or session.get("payment_status") != "paid"
            or session.get("amount_total") != tx.get("amount_cents")
            or (session.get("currency") or "").lower() != "eur"
            or metadata.get("gift_order_id") != str(tx.get("_id"))
            or session.get("client_reference_id") != str(tx.get("_id"))
            or len(line_items) != 1):
        raise ValueError("La session Stripe ne correspond pas à la commande")
    item = line_items[0]
    price = _stripe_object(item.get("price") or {})
    product = price.get("product") or {}
    product_id = product.get("id") if isinstance(product, dict) else product
    if (item.get("quantity") != 1 or price.get("id") != tx.get("stripe_price_id")
            or product_id != tx.get("stripe_product_id")
            or price.get("unit_amount") != tx.get("amount_cents")
            or (price.get("currency") or "").lower() != "eur"
            or price.get("type") != "one_time"):
        raise ValueError("Le tarif Stripe ne correspond pas à l'offre")
    intent = _stripe_object(session.get("payment_intent") or {})
    charge = intent.get("latest_charge") or {}
    if isinstance(charge, str):
        raise ValueError("Le paiement Stripe n'est pas vérifiable")
    charge_created = charge.get("created") if isinstance(charge, dict) else None
    if not charge_created:
        raise ValueError("Le paiement Stripe n'a pas de confirmation immédiate")
    paid_at = datetime.fromtimestamp(charge_created, timezone.utc)
    if tx.get("gift", {}).get("is_christmas") and paid_at >= SALE_CUTOFF:
        raise ValueError("Le paiement Noël a été effectué après la fermeture de l'offre")
    return {"payment_intent_id": intent.get("id"), "charge_id": charge.get("id"),
            "paid_at": paid_at}


async def _confirm_platform_order(tx: dict) -> Optional[dict]:
    st = await _platform_checkout().get_checkout_status(tx["session_id"])
    if st.payment_status != "paid":
        await db.payment_transactions.update_one({"_id": tx["_id"]}, {"$set": {
            "payment_status": st.payment_status, "status": st.status}})
        return None
    if (st.amount_total != tx.get("amount_cents") or (st.currency or "").lower() != "eur"
            or (st.metadata or {}).get("gift_order_id") != str(tx["_id"])):
        raise ValueError("La session Stripe ne correspond pas à la commande")
    paid_at = datetime.now(timezone.utc)
    if tx.get("gift", {}).get("is_christmas") and paid_at >= SALE_CUTOFF:
        raise ValueError("Le paiement Noël a été effectué après la fermeture de l'offre")
    delivery_status = "queued" if tx.get("gift", {}).get("delivery_method") == "direct" else "not_required"
    await db.payment_transactions.update_one({"_id": tx["_id"]}, {"$set": {
        "payment_status": "paid", "status": "complete", "stripe_verified": True,
        "gift_delivery_status": delivery_status, "paid_at": paid_at}})
    return await db.payment_transactions.find_one({"_id": tx["_id"]})


async def _confirm_gift_order(tx: dict) -> Optional[dict]:
    if tx.get("payment_status") == "paid" and tx.get("stripe_verified") is True:
        return tx
    if tx.get("stripe_mode") == "platform":
        return await _confirm_platform_order(tx)
    session = await _retrieve_checkout_session(tx)
    session_data = _stripe_object(session)
    if session_data.get("payment_status") != "paid":
        await db.payment_transactions.update_one({"_id": tx["_id"]}, {"$set": {
            "payment_status": session_data.get("payment_status", "unpaid"),
            "status": session_data.get("status", "open"),
        }})
        return None
    verified = _validate_paid_session(tx, session)
    delivery_status = "queued" if tx.get("gift", {}).get("delivery_method") == "direct" else "not_required"
    await db.payment_transactions.update_one({"_id": tx["_id"]}, {"$set": {
        "payment_status": "paid", "status": "complete", "stripe_verified": True,
        "gift_delivery_status": delivery_status,
        **verified,
    }})
    return await db.payment_transactions.find_one({"_id": tx["_id"]})


async def process_gift_stripe_event(event: dict, mode: str) -> None:
    event = _stripe_object(event)
    event_type = event.get("type")
    if event_type not in {"checkout.session.completed", "checkout.session.async_payment_succeeded",
                          "checkout.session.expired"}:
        return
    session_event = ((event.get("data") or {}).get("object") or {})
    metadata = session_event.get("metadata") or {}
    raw_order_id = metadata.get("gift_order_id")
    if not raw_order_id:
        return
    try:
        order_id = ObjectId(raw_order_id)
    except Exception as exc:
        raise ValueError("Référence de commande cadeau invalide") from exc
    tx = await db.payment_transactions.find_one({"_id": order_id, "stripe_mode": mode,
                                                 "gift": {"$exists": True}})
    if not tx:
        raise ValueError("Commande cadeau correspondante introuvable")
    stripe_session_id = session_event.get("id")
    if not stripe_session_id:
        raise ValueError("Session Stripe absente de l'événement")
    if tx.get("session_id", "").startswith("pending:"):
        await db.payment_transactions.update_one(
            {"_id": order_id, "session_id": tx["session_id"], "stripe_mode": mode},
            {"$set": {"session_id": stripe_session_id}},
        )
        tx = await db.payment_transactions.find_one({"_id": order_id})
    if tx.get("session_id") != stripe_session_id:
        raise ValueError("La session Stripe ne correspond pas à la commande")
    if event_type == "checkout.session.expired":
        await db.payment_transactions.update_one(
            {"_id": order_id, "session_id": stripe_session_id, "payment_status": {"$ne": "paid"}},
            {"$set": {"status": "expired", "payment_status": "unpaid"}},
        )
        return
    try:
        tx = await _confirm_gift_order(tx)
    except Exception:
        logger.exception("Vérification de paiement cadeau impossible (order=%s)", order_id)
        raise
    if not tx:
        return
    gift = await fulfill_gift_transaction(tx)
    await _ensure_gift_pdf(gift)


async def deliver_scheduled_gift_cards() -> None:
    now = datetime.now(timezone.utc)
    if not RESEND_API_KEY:
        return
    cursor = db.payment_transactions.find({
        "gift.delivery_method": "direct", "gift.delivery_at": {"$lte": now},
        "payment_status": "paid", "stripe_verified": True,
        "$or": [
            {"gift_delivery_status": "queued"},
            {"gift_delivery_status": "retry", "gift_delivery_retry_at": {"$lte": now}},
            {"gift_delivery_status": "sending", "gift_delivery_lease_until": {"$lt": now}},
        ],
    }).limit(30)
    async for tx in cursor:
        lease = now + timedelta(minutes=5)
        claimed = await db.payment_transactions.find_one_and_update(
            {"_id": tx["_id"], "payment_status": "paid", "stripe_verified": True,
             "$or": [
                 {"gift_delivery_status": "queued"},
                 {"gift_delivery_status": "retry", "gift_delivery_retry_at": {"$lte": now}},
                 {"gift_delivery_status": "sending", "gift_delivery_lease_until": {"$lt": now}},
             ]},
            {"$set": {"gift_delivery_status": "sending", "gift_delivery_lease_until": lease}},
            return_document=ReturnDocument.AFTER,
        )
        if not claimed:
            continue
        try:
            gift = await db.gift_codes.find_one({"order_id": tx["_id"]})
            if not gift:
                gift = await fulfill_gift_transaction(claimed)
            if not await _ensure_gift_pdf(gift):
                raise RuntimeError("PDF indisponible")
            gift = await db.gift_codes.find_one({"_id": gift["_id"]})
            bucket = AsyncIOMotorGridFSBucket(db, bucket_name=PDF_BUCKET)
            stream = await bucket.open_download_stream(gift["pdf_file_id"])
            pdf_data = await stream.read()
            recipient = claimed["gift"]["recipient_email"]
            code = _reveal_code(gift)
            html_body = (
                f"<p>Bonjour {html.escape(claimed['gift']['recipient_name'])},</p>"
                "<p>Vous recevez une carte cadeau GénéraQuiz. Votre année d’accès commencera "
                "à l’activation du code figurant sur la carte jointe.</p>"
                f"<p><a href=\"{FRONTEND_URL.rstrip('/')}/activer?code={code}\">Activer mon cadeau</a></p>"
            )
            await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL, "to": [recipient],
                "subject": "Votre carte cadeau GénéraQuiz",
                "html": html_body,
                "attachments": [{"filename": "carte-cadeau-generaquiz.pdf",
                                 "content": base64.b64encode(pdf_data).decode("ascii")}],
            })
            await db.payment_transactions.update_one(
                {"_id": tx["_id"], "gift_delivery_status": "sending"},
                {"$set": {"gift_delivery_status": "sent", "gift_delivery_sent_at": datetime.now(timezone.utc)},
                 "$unset": {"gift_delivery_lease_until": ""}},
            )
        except Exception as exc:
            logger.warning("Envoi cadeau différé en échec (commande=%s, erreur=%s)", tx["_id"], type(exc).__name__)
            await db.payment_transactions.update_one(
                {"_id": tx["_id"], "gift_delivery_status": "sending"},
                {"$set": {"gift_delivery_status": "retry", "gift_delivery_retry_at": now + timedelta(minutes=5)},
                 "$unset": {"gift_delivery_lease_until": ""}},
            )


async def close_expired_christmas_checkouts() -> None:
    if datetime.now(timezone.utc) < SALE_CUTOFF:
        return
    cursor = db.payment_transactions.find({
        "gift.is_christmas": True,
        "payment_status": {"$ne": "paid"},
        "status": "open",
        "session_id": {"$regex": r"^cs_"},
    }).limit(100)
    async for tx in cursor:
        try:
            if tx.get("stripe_mode") == "platform":
                confirmed = await _confirm_gift_order(tx)
                if confirmed:
                    await _ensure_gift_pdf(await fulfill_gift_transaction(confirmed))
                else:
                    await db.payment_transactions.update_one(
                        {"_id": tx["_id"], "payment_status": {"$ne": "paid"}},
                        {"$set": {"status": "expired", "payment_status": "unpaid"}})
                continue
            session = await _retrieve_checkout_session(tx)
            session_data = _stripe_object(session)
            if session_data.get("payment_status") == "paid":
                confirmed = await _confirm_gift_order(tx)
                if confirmed:
                    gift = await fulfill_gift_transaction(confirmed)
                    await _ensure_gift_pdf(gift)
            elif session_data.get("status") == "open":
                config = _stripe_config(tx.get("stripe_mode"), tx.get("gift", {}).get("offer"))
                stripe.api_key = config["api_key"]
                await asyncio.to_thread(stripe.checkout.Session.expire, tx["session_id"])
                await db.payment_transactions.update_one(
                    {"_id": tx["_id"], "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": "expired", "payment_status": "unpaid"}},
                )
            else:
                await db.payment_transactions.update_one(
                    {"_id": tx["_id"], "payment_status": {"$ne": "paid"}},
                    {"$set": {"status": session_data.get("status", "expired"),
                              "payment_status": session_data.get("payment_status", "unpaid")}},
                )
        except Exception as exc:
            logger.warning("Clôture Stripe différée pour commande %s (%s)", tx.get("_id"), type(exc).__name__)


@router.get("/gifts/order/{session_id}")
async def gift_order_status(session_id: str, access_token: str, request: Request) -> dict:
    tx = await db.payment_transactions.find_one({"session_id": session_id, "gift": {"$exists": True}})
    if not tx or not hmac.compare_digest(tx.get("buyer_access_hash", ""), _buyer_access_hash(access_token)):
        raise HTTPException(status_code=404, detail="Commande introuvable")
    try:
        tx = await _confirm_gift_order(tx)
    except Exception:
        logger.warning("Vérification Stripe impossible pour commande cadeau %s", tx.get("_id"))
        raise HTTPException(status_code=503, detail="Le paiement est en cours de vérification")
    if not tx:
        return {"payment_status": "unpaid", "status": "open"}
    g = await fulfill_gift_transaction(tx)
    pdf_ready = await _ensure_gift_pdf(g)
    token = _download_token(str(tx["_id"])) if pdf_ready else None
    return {"payment_status": "paid", "status": "complete", "gift": _gift_public(g),
            "pdf_status": "ready" if pdf_ready else "preparing",
            "pdf_url": f"/api/gifts/order/{session_id}/carte.pdf?token={token}" if token else None}


@router.get("/gifts/order/{session_id}/carte.pdf")
async def gift_order_pdf(session_id: str, token: str) -> Response:
    tx = await db.payment_transactions.find_one({"session_id": session_id, "gift": {"$exists": True}})
    if not tx or not _valid_download_token(token, str(tx["_id"])):
        raise HTTPException(status_code=404, detail="Carte introuvable ou lien expiré")
    if tx.get("payment_status") != "paid" or tx.get("stripe_verified") is not True:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    gift = await db.gift_codes.find_one({"order_id": tx["_id"]})
    if not gift:
        raise HTTPException(status_code=404, detail="Carte introuvable")
    if not gift.get("pdf_file_id"):
        if not await _ensure_gift_pdf(gift):
            return JSONResponse(status_code=202, content={"status": "preparing"})
        gift = await db.gift_codes.find_one({"_id": gift["_id"]})
    return await _pdf_response(gift)


@router.get("/gifts/code/{code}", dependencies=[Depends(rate_limit("gift_lookup", 20, 60))])
async def gift_lookup(code: str) -> dict:
    g = await _find_gift_by_code(code)
    if not g or g["status"] in {"cancelled", "revoked"}:
        raise HTTPException(status_code=404, detail="Ce code cadeau est introuvable. Vérifiez les lettres et chiffres.")
    return _gift_public(g)


@router.get("/gifts/{code}/carte.pdf")
async def gift_pdf(code: str, k: str) -> Response:
    g = await _find_gift_by_code(code)
    if not g or g["status"] in {"cancelled", "revoked"} or not secrets.compare_digest(g["pdf_key"], k):
        raise HTTPException(status_code=404, detail="Carte introuvable")
    if not g.get("pdf_file_id") and not await _ensure_gift_pdf(g):
        return JSONResponse(status_code=202, content={"status": "preparing"})
    g = await db.gift_codes.find_one({"_id": g["_id"]})
    return await _pdf_response(g)


async def _pdf_response(g: dict) -> Response:
    bucket = AsyncIOMotorGridFSBucket(db, bucket_name=PDF_BUCKET)
    try:
        stream = await bucket.open_download_stream(g["pdf_file_id"])
        pdf = await stream.read()
    except Exception:
        await db.gift_codes.update_one({"_id": g["_id"]}, {"$unset": {"pdf_file_id": ""},
                                                               "$set": {"pdf_status": "failed"}})
        raise HTTPException(status_code=404, detail="Carte en cours de régénération")
    code = _reveal_code(g)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="carte-cadeau-{code[-4:]}.pdf"',
                             "Cache-Control": "private, no-store"})


class GiftRedeem(BaseModel):
    code: str = Field(..., min_length=4, max_length=48)


@router.post("/gifts/redeem", dependencies=[Depends(rate_limit("gift_redeem", 10, 60))])
async def gift_redeem(body: GiftRedeem, user: dict = Depends(get_current_user)) -> dict:
    code = normalize_code(body.code)
    now = datetime.now(timezone.utc)
    normalized = normalize_code(code)
    if not normalized:
        raise HTTPException(status_code=404, detail="Ce code cadeau est introuvable. Vérifiez les lettres et chiffres.")
    user_id = user["_id"]

    async def _activate(session):
        g = await db.gift_codes.find_one_and_update(
            {"status": {"$in": ["available", "active"]}, "$or": [
                {"code_hash": _hash_code(normalized)}, {"code": normalized},
            ]},
            {"$set": {"status": "activated", "activated_at": now,
                      "beneficiary_id": str(user_id), "beneficiary_email": user["email"]}},
            return_document=ReturnDocument.BEFORE, session=session,
        )
        if not g:
            exists = await db.gift_codes.find_one(
                {"$or": [{"code_hash": _hash_code(normalized)}, {"code": normalized}]},
                {"status": 1}, session=session,
            )
            if exists and exists["status"] in {"activated", "redeemed"}:
                raise HTTPException(status_code=409, detail="Ce code cadeau a déjà été activé.")
            raise HTTPException(status_code=404, detail="Ce code cadeau est introuvable. Vérifiez les lettres et chiffres.")
        current = await db.users.find_one({"_id": user_id}, session=session)
        if not current:
            raise HTTPException(status_code=401, detail="Connectez-vous pour activer ce cadeau")
        tier = g["tier"]
        current_active = is_premium_active(current)
        keep_lifetime = current_active and not current.get("plan_expires_at")
        base = now
        if current_active:
            try:
                current_expiry = datetime.fromisoformat(current["plan_expires_at"])
                base = max(now, current_expiry if current_expiry.tzinfo else current_expiry.replace(tzinfo=timezone.utc))
            except (KeyError, TypeError, ValueError):
                pass
            current_tier = current.get("plan_tier")
            if (TIER_RANK.get(current_tier, 0) > TIER_RANK[tier]
                    or (tier == NOEL_TIER and current_tier in {"famille", "famille_v2", "heritage", "premium"})):
                tier = current_tier
            elif current_tier == NOEL_TIER and tier == "famille_v2":
                tier = "famille_v2"
        try:
            expires = None if keep_lifetime else base.replace(year=base.year + 1)
        except ValueError:
            expires = base.replace(year=base.year + 1, day=28)
        expires_value = expires.isoformat() if expires else None
        await db.users.update_one({"_id": user_id}, {"$set": {
            "plan": "premium", "plan_tier": tier,
            "plan_period": current.get("plan_period") if keep_lifetime else "yearly",
            "plan_expires_at": expires_value, **family_subscription_fields(current, tier)}}, session=session)
        await db.gift_codes.update_one({"_id": g["_id"]}, {"$set": {
            "plan_expires_at": expires, "activation_order_id": str(g.get("order_id") or "")}},
            session=session)
        return g, tier, expires, family_subscription_fields(current, tier).get("family_max_proches")

    try:
        try:
            async with await client.start_session() as session:
                async with session.start_transaction():
                    g, tier, expires, capacity = await _activate(session)
        except OperationFailure as exc:
            if exc.code != 20:  # 20 = MongoDB autonome (aperçu) : pas de transactions
                raise
            g, tier, expires, capacity = await _activate(None)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Activation cadeau transactionnelle échouée (user=%s)", user_id)
        raise HTTPException(status_code=503, detail="Activation temporairement indisponible") from exc
    return {"ok": True, "offer": g["offer"], "offer_label": OFFERS[g["offer"]]["label"],
            "plan_tier": tier, "plan_expires_at": expires.isoformat() if expires else None,
            "max_proches": capacity or (3 if tier == NOEL_TIER else 4)}


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
            "activated_at": g.get("activated_at", g.get("redeemed_at")),
            "redeemed_by_email": g.get("beneficiary_email", g.get("redeemed_by_email")),
            "plan_expires_at": g.get("plan_expires_at"), "pdf_url": _pdf_url(g)}


@router.get("/admin/gifts")
async def admin_list_gifts(admin: dict = Depends(get_admin_user)) -> dict:
    rows = await db.gift_codes.find().sort("created_at", -1).to_list(1000)
    paid = [r for r in rows if r.get("source") == "stripe"]
    return {"gifts": [_gift_admin(r) for r in rows],
            "stats": {"sold": len(paid), "revenue": round(sum(r.get("amount", 0) for r in paid), 2),
                  "redeemed": sum(1 for r in rows if r["status"] in {"activated", "redeemed"}),
                  "pending": sum(1 for r in rows if r["status"] in {"available", "active"})}}


@router.post("/admin/gifts")
async def admin_create_gift(body: AdminGiftCreate, admin: dict = Depends(get_admin_user)) -> dict:
    g = await _insert_gift({"offer": body.offer, "tier": OFFERS[body.offer]["tier"], "amount": 0,
                            "theme": body.theme, "recipient_name": _clean(body.recipient_name),
                            "buyer_name": _clean(body.buyer_name), "message": _clean(body.message),
                            "source": "admin", "session_id": f"admin-{ObjectId()}",
                            "created_by": str(admin["_id"])})
    await record_audit(admin, action="gift.create", target_type="gift", target_label=f"…{g['code'][-4:]}",
                       meta={"offer": body.offer})
    return _gift_admin(g)


@router.patch("/admin/gifts/{code}/cancel")
async def admin_cancel_gift(code: str, admin: dict = Depends(get_admin_user)) -> dict:
    normalized = normalize_code(code)
    if not normalized:
        raise HTTPException(status_code=400, detail="Code cadeau invalide")
    g = await db.gift_codes.find_one_and_update(
        {"status": {"$in": ["available", "active"]}, "$or": [
            {"code_hash": _hash_code(normalized)}, {"code": normalized},
        ]},
        {"$set": {"status": "revoked"}}, return_document=ReturnDocument.AFTER,
    )
    if not g:
        raise HTTPException(status_code=400, detail="Seul un code non activé peut être annulé")
    await record_audit(admin, action="gift.cancel", target_type="gift", target_label=f"…{g.get('code_last4', '')}")
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
    """Index uniques + sparse ; remplace un ancien index au même nom mais aux options différentes."""
    existing = await db.gift_codes.index_information()
    for field in ("code", "code_hash", "order_id", "session_id"):
        old = existing.get(f"{field}_1")
        if old and not (old.get("unique") and old.get("sparse")):
            await db.gift_codes.drop_index(f"{field}_1")
        try:
            await db.gift_codes.create_index(field, unique=True, sparse=True)
        except Exception as e:  # ne jamais bloquer le démarrage sur un index
            logger.error(f"[gifts] index {field} non créé : {e}")
