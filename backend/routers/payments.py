"""Payments router: Stripe checkout + webhook + packages."""
import asyncio
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse,
)

from core import (
    db, logger, STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET, PACKAGES, get_current_user, CheckoutCreate,
    GIFT_STRIPE_TEST_WEBHOOK_SECRET, GIFT_STRIPE_LIVE_WEBHOOK_SECRET,
)

router = APIRouter(tags=["payments"])


@router.get("/packages")
async def list_packages():
    return [{"id": pid, **pkg} for pid, pkg in PACKAGES.items()]


@router.get("/pricing/summary/{package_id}")
async def pricing_summary(package_id: str):
    from subscription import check_package_sellable, summary_text
    pkg = check_package_sellable(package_id)
    return {"package_id": package_id, "amount": pkg["amount"], "renew_amount": pkg["renew_amount"],
            "period": pkg["period"], "promo": bool(pkg.get("promo")), "summary": summary_text(pkg)}


@router.post("/checkout/session")
async def create_checkout(body: CheckoutCreate, user: dict = Depends(get_current_user)):
    from subscription import check_package_sellable, create_checkout_session
    pkg = check_package_sellable(body.package_id)
    if not body.accept_terms:
        raise HTTPException(status_code=400, detail="Merci d'accepter les conditions et le renouvellement avant de payer")
    try:
        session = await asyncio.to_thread(create_checkout_session, pkg, body.package_id, user, body.origin_url.rstrip("/"))
    except Exception as e:
        logger.error(f"[checkout] session Stripe impossible : {e}")
        raise HTTPException(status_code=502, detail="Le paiement n'a pas pu s'ouvrir. Réessayez dans un instant.")
    await db.payment_transactions.insert_one({
        "session_id": session["id"], "user_id": str(user["_id"]),
        "user_email": user["email"], "package_id": body.package_id,
        "amount": float(pkg["amount"]), "currency": pkg["currency"], "mode": "subscription",
        "metadata": {"package_id": body.package_id, "accepted_terms_at": datetime.now(timezone.utc).isoformat()},
        "payment_status": "initiated", "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session["url"], "session_id": session["id"]}


@router.get("/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, user: dict = Depends(get_current_user)):
    from subscription import _stripe, activate_from_session
    tx = await db.payment_transactions.find_one({"session_id": session_id, "user_id": str(user["_id"])})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    if tx["payment_status"] != "paid":
        sess = await asyncio.to_thread(_stripe().checkout.Session.retrieve, session_id)
        if sess.get("status") == "complete" and sess.get("payment_status") in ("paid", "no_payment_required"):
            await activate_from_session(session_id)
        else:
            await db.payment_transactions.update_one({"session_id": session_id},
                                                      {"$set": {"payment_status": sess.get("payment_status"),
                                                                "status": sess.get("status")}})
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    return {"session_id": session_id, "payment_status": tx["payment_status"], "status": tx["status"],
            "amount_total": round(tx["amount"] * 100), "currency": tx["currency"]}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    gift_event = None
    gift_mode = None
    for mode, secret in (("test", GIFT_STRIPE_TEST_WEBHOOK_SECRET),
                         ("live", GIFT_STRIPE_LIVE_WEBHOOK_SECRET)):
        if not secret:
            continue
        try:
            gift_event = stripe.Webhook.construct_event(body, sig, secret)
            gift_mode = mode
            break
        except Exception:
            continue
    if gift_event is not None:
        if bool(gift_event.get("livemode")) != (gift_mode == "live"):
            raise HTTPException(status_code=400, detail="Environnement Stripe incorrect")
        try:
            from routers.gifts import process_gift_stripe_event
            await process_gift_stripe_event(gift_event, gift_mode)
        except Exception as e:
            logger.error("Traitement webhook cadeau impossible : %s", type(e).__name__)
            raise HTTPException(status_code=500, detail="Événement Stripe à réessayer") from e
        return {"ok": True}

    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Signature Stripe invalide")
    host_url = str(request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    try:
        evt = await stripe_checkout.handle_webhook(body, sig)
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return {"ok": False}
    if evt.payment_status == "paid":
        tx = await db.payment_transactions.find_one({"session_id": evt.session_id})
        if tx and tx.get("gift"):
            from routers.gifts import fulfill_gift_transaction, _confirm_gift_order
            confirmed = await _confirm_gift_order(tx)
            if confirmed:
                await fulfill_gift_transaction(confirmed)
            await db.payment_transactions.update_one({"session_id": evt.session_id},
                                                      {"$set": {"payment_status": "paid", "status": "complete"}})
        elif tx and tx["payment_status"] != "paid":
            from subscription import activate_from_session
            await activate_from_session(evt.session_id)
    return {"ok": True}
