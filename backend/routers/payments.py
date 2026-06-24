"""Payments router: Stripe checkout + webhook + packages."""
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse,
)

from core import db, logger, STRIPE_API_KEY, PACKAGES, get_current_user, CheckoutCreate

router = APIRouter(tags=["payments"])


@router.get("/packages")
async def list_packages():
    return [{"id": pid, **pkg} for pid, pkg in PACKAGES.items()]


@router.post("/checkout/session")
async def create_checkout(body: CheckoutCreate, request: Request, user: dict = Depends(get_current_user)):
    if body.package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail="Forfait invalide")
    pkg = PACKAGES[body.package_id]
    host_url = str(request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/app/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/app/pricing"
    session = await stripe_checkout.create_checkout_session(CheckoutSessionRequest(
        amount=float(pkg["amount"]), currency=pkg["currency"],
        success_url=success_url, cancel_url=cancel_url,
        metadata={"user_id": str(user["_id"]), "user_email": user["email"], "package_id": body.package_id},
    ))
    await db.payment_transactions.insert_one({
        "session_id": session.session_id, "user_id": str(user["_id"]),
        "user_email": user["email"], "package_id": body.package_id,
        "amount": float(pkg["amount"]), "currency": pkg["currency"],
        "metadata": {"package_id": body.package_id},
        "payment_status": "initiated", "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.session_id}


@router.get("/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    host_url = str(request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    status = await stripe_checkout.get_checkout_status(session_id)
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    if tx["payment_status"] != "paid" and status.payment_status == "paid":
        package_id = tx.get("package_id", "premium_monthly")
        days = 365 if package_id == "premium_yearly" else 30
        expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        await db.users.update_one({"_id": ObjectId(tx["user_id"])},
                                  {"$set": {"plan": "premium", "plan_expires_at": expires}})
    await db.payment_transactions.update_one({"session_id": session_id},
                                              {"$set": {"payment_status": status.payment_status, "status": status.status}})
    return {"session_id": session_id, "payment_status": status.payment_status,
            "status": status.status, "amount_total": status.amount_total, "currency": status.currency}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
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
        if tx and tx["payment_status"] != "paid":
            package_id = tx.get("package_id", "premium_monthly")
            days = 365 if package_id == "premium_yearly" else 30
            expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
            await db.users.update_one({"_id": ObjectId(tx["user_id"])},
                                      {"$set": {"plan": "premium", "plan_expires_at": expires}})
            await db.payment_transactions.update_one({"session_id": evt.session_id},
                                                      {"$set": {"payment_status": "paid", "status": "complete"}})
    return {"ok": True}
