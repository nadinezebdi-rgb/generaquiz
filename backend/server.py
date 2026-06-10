"""Quiz d'Antan SaaS - FastAPI backend with JWT auth, quiz catalog, Stripe subscriptions."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import secrets
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Annotated

import bcrypt
import jwt
import resend
from bson import ObjectId
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field, BeforeValidator, ConfigDict
from starlette.middleware.cors import CORSMiddleware

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CheckoutStatusResponse,
)

from seed_data import CATEGORIES, QUESTIONS

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@quizdantan.fr")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin2026!")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Subscription packages (server-side defined for security)
PACKAGES: Dict[str, Dict[str, Any]] = {
    "premium_monthly": {
        "amount": 9.99,
        "currency": "eur",
        "label": "Premium Mensuel",
        "description": "Accès illimité aux quiz, activités et défis famille",
    },
    "premium_yearly": {
        "amount": 89.99,
        "currency": "eur",
        "label": "Premium Annuel",
        "description": "12 mois — économisez 2 mois",
    },
}

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("quizdantan")

app = FastAPI(title="Quiz d'Antan API")
api = APIRouter(prefix="/api")

# Static files for generated mascot images
STATIC_DIR = ROOT_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "mascots").mkdir(exist_ok=True)
app.mount("/api/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _oid(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    return str(v)


PyObjectId = Annotated[str, BeforeValidator(_oid)]


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=7 * 24 * 3600, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="none", max_age=30 * 24 * 3600, path="/")


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def user_to_public(u: dict) -> dict:
    return {
        "id": str(u["_id"]),
        "email": u["email"],
        "name": u.get("name", ""),
        "role": u.get("role", "user"),
        "plan": u.get("plan", "free"),
        "plan_expires_at": u.get("plan_expires_at"),
        "created_at": u.get("created_at"),
    }


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token invalide")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Utilisateur introuvable")
        # Keep _id as ObjectId for internal queries; never returned directly.
        return dict(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expirée")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")


async def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès administrateur requis")
    return user


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=6)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6)


class UpdateProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class AttemptCreate(BaseModel):
    category_id: str
    score: int
    total: int
    duration_seconds: Optional[int] = None


class CheckoutCreate(BaseModel):
    package_id: str
    origin_url: str


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@api.get("/")
async def root():
    return {"status": "ok", "app": "Quiz d'Antan"}


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@api.post("/auth/register")
async def register(body: RegisterRequest, response: Response):
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")
    doc = {
        "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name.strip(),
        "role": "user",
        "plan": "free",
        "plan_expires_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    access = create_access_token(str(result.inserted_id), email)
    refresh = create_refresh_token(str(result.inserted_id))
    set_auth_cookies(response, access, refresh)
    return {"user": user_to_public(doc), "access_token": access}


@api.post("/auth/login")
async def login(body: LoginRequest, response: Response):
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    access = create_access_token(str(user["_id"]), email)
    refresh = create_refresh_token(str(user["_id"]))
    set_auth_cookies(response, access, refresh)
    return {"user": user_to_public(user), "access_token": access}


@api.post("/auth/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user_to_public(user)


def _build_reset_email_html(reset_link: str) -> str:
    """Inline-styled HTML email for password reset (French)."""
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Réinitialiser votre mot de passe</title></head>
<body style="margin:0;padding:0;background-color:#F4F1DE;font-family:Arial,Helvetica,sans-serif;color:#1A2530;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F4F1DE;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background-color:#FFFFFF;border-radius:24px;border:2px solid #E8E2C9;overflow:hidden;">
        <tr><td style="background-color:#1E3A5F;padding:30px;text-align:center;">
          <div style="display:inline-block;background-color:#E07A5F;width:48px;height:48px;border-radius:50%;line-height:48px;color:#FFFFFF;font-size:24px;font-weight:bold;">Q</div>
          <h1 style="color:#F2CC8F;font-family:Georgia,serif;font-size:28px;margin:14px 0 0;">Quiz d'Antan</h1>
        </td></tr>
        <tr><td style="padding:40px 32px;">
          <h2 style="font-family:Georgia,serif;font-size:24px;color:#1A2530;margin:0 0 16px;">Réinitialisation de votre mot de passe</h2>
          <p style="font-size:16px;line-height:1.6;color:#334155;margin:0 0 20px;">Bonjour,</p>
          <p style="font-size:16px;line-height:1.6;color:#334155;margin:0 0 20px;">Vous avez demandé à réinitialiser le mot de passe de votre compte <strong>Quiz d'Antan</strong>. Cliquez sur le bouton ci-dessous pour choisir un nouveau mot de passe :</p>
          <table cellpadding="0" cellspacing="0" style="margin:28px auto;"><tr><td style="background-color:#E07A5F;border-radius:30px;">
            <a href="{reset_link}" style="display:inline-block;padding:16px 36px;color:#FFFFFF;text-decoration:none;font-weight:bold;font-size:16px;font-family:Arial,sans-serif;">Réinitialiser mon mot de passe</a>
          </td></tr></table>
          <p style="font-size:14px;line-height:1.6;color:#64748B;margin:20px 0 8px;">Ou copiez-collez ce lien dans votre navigateur :</p>
          <p style="font-size:13px;line-height:1.4;color:#1E3A5F;word-break:break-all;background-color:#F4F1DE;padding:12px;border-radius:8px;margin:0 0 24px;font-family:monospace;">{reset_link}</p>
          <p style="font-size:14px;line-height:1.6;color:#64748B;margin:20px 0;">Ce lien est valable <strong>1 heure</strong>.</p>
          <p style="font-size:14px;line-height:1.6;color:#64748B;margin:20px 0 0;">Si vous n'avez pas demandé cette réinitialisation, ignorez simplement cet email — votre mot de passe reste inchangé.</p>
        </td></tr>
        <tr><td style="background-color:#F4F1DE;padding:20px 32px;text-align:center;border-top:2px solid #E8E2C9;">
          <p style="font-size:12px;color:#64748B;margin:0;">© Quiz d'Antan — La plateforme de jeux de mémoire pour seniors</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


async def _send_reset_email(to_email: str, reset_link: str) -> bool:
    """Send the password reset email via Resend (non-blocking). Returns True on success."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — email not sent")
        return False
    params = {
        "from": SENDER_EMAIL,
        "to": [to_email],
        "subject": "Réinitialisation de votre mot de passe — Quiz d'Antan",
        "html": _build_reset_email_html(reset_link),
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        eid = result.get("id") if isinstance(result, dict) else result
        logger.info(f"Reset email sent to {to_email} — id={eid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reset email to {to_email}: {e}")
        return False


@api.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Always returns success (no user enumeration). If the user exists,
    generates a reset token and sends the reset link via email."""
    email = body.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        return {"ok": True, "message": "Si ce compte existe, un email de réinitialisation a été envoyé."}
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    await db.password_reset_tokens.insert_one({
        "token": token,
        "user_id": str(user["_id"]),
        "email": email,
        "expires_at": expires_at,
        "used": False,
        "created_at": datetime.now(timezone.utc),
    })
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
    logger.info(f"[RESET] {email} -> {reset_link}")
    sent = await _send_reset_email(email, reset_link)
    return {"ok": True, "message": "Si ce compte existe, un email de réinitialisation a été envoyé.", "email_sent": sent}


@api.post("/auth/reset-password")
async def reset_password(body: ResetPasswordRequest):
    record = await db.password_reset_tokens.find_one({"token": body.token})
    if not record:
        raise HTTPException(status_code=400, detail="Lien invalide ou expiré")
    if record.get("used"):
        raise HTTPException(status_code=400, detail="Lien déjà utilisé")
    expires = record.get("expires_at")
    if isinstance(expires, datetime):
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Lien expiré")
    new_hash = hash_password(body.new_password)
    await db.users.update_one(
        {"_id": ObjectId(record["user_id"])},
        {"$set": {"password_hash": new_hash}},
    )
    await db.password_reset_tokens.update_one(
        {"_id": record["_id"]}, {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}}
    )
    return {"ok": True, "message": "Mot de passe réinitialisé. Vous pouvez vous connecter."}


@api.post("/auth/change-password")
async def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    new_hash = hash_password(body.new_password)
    await db.users.update_one({"_id": ObjectId(str(user["_id"]))}, {"$set": {"password_hash": new_hash}})
    return {"ok": True, "message": "Mot de passe mis à jour"}


@api.patch("/auth/profile")
async def update_profile(body: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"_id": ObjectId(str(user["_id"]))}, {"$set": {"name": body.name.strip()}}
    )
    fresh = await db.users.find_one({"_id": ObjectId(str(user["_id"]))})
    return user_to_public(fresh)


@api.delete("/auth/account")
async def delete_account(user: dict = Depends(get_current_user), response: Response = None):
    user_id = str(user["_id"])
    await db.users.delete_one({"_id": ObjectId(user_id)})
    await db.attempts.delete_many({"user_id": user_id})
    await db.challenges.delete_many({"creator_user_id": user_id})
    if response is not None:
        clear_auth_cookies(response)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Quiz catalog endpoints
# ---------------------------------------------------------------------------
@api.get("/categories")
async def list_categories():
    cats = await db.categories.find({}, {"_id": 0}).to_list(100)
    return cats


@api.get("/categories/{category_id}/questions")
async def get_questions(category_id: str, user: dict = Depends(get_current_user)):
    # Free users get 5 questions per quiz; Premium uses the full pool (up to 30)
    limit = 30 if user.get("plan") == "premium" else 5
    cat = await db.categories.find_one({"id": category_id}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    # Random sample from the full pool for variety (Mongo $sample)
    pipeline = [
        {"$match": {"category_id": category_id}},
        {"$sample": {"size": limit}},
        {"$project": {"_id": 0}},
    ]
    qs = await db.questions.aggregate(pipeline).to_list(limit)
    return {"category": cat, "questions": qs, "is_premium": user.get("plan") == "premium"}


@api.post("/attempts")
async def save_attempt(body: AttemptCreate, user: dict = Depends(get_current_user)):
    doc = {
        "user_id": str(user["_id"]),
        "category_id": body.category_id,
        "score": body.score,
        "total": body.total,
        "duration_seconds": body.duration_seconds,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.attempts.insert_one(doc)
    return {"ok": True}


@api.get("/attempts")
async def list_attempts(user: dict = Depends(get_current_user)):
    rows = await db.attempts.find({"user_id": str(user["_id"])}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rows


@api.get("/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    total = await db.attempts.count_documents({"user_id": str(user["_id"])})
    pipeline = [
        {"$match": {"user_id": str(user["_id"])}},
        {"$group": {"_id": None, "score": {"$sum": "$score"}, "total": {"$sum": "$total"}}},
    ]
    agg = await db.attempts.aggregate(pipeline).to_list(1)
    if agg:
        s, t = agg[0]["score"], agg[0]["total"]
        pct = round((s / t) * 100) if t else 0
    else:
        s, t, pct = 0, 0, 0
    return {"quizzes_played": total, "correct_answers": s, "total_answers": t, "accuracy_pct": pct}


# ---------------------------------------------------------------------------
# Stripe Checkout subscription
# ---------------------------------------------------------------------------
@api.post("/checkout/session")
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

    checkout_request = CheckoutSessionRequest(
        amount=float(pkg["amount"]),
        currency=pkg["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": str(user["_id"]),
            "user_email": user["email"],
            "package_id": body.package_id,
        },
    )
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)

    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": str(user["_id"]),
        "user_email": user["email"],
        "package_id": body.package_id,
        "amount": float(pkg["amount"]),
        "currency": pkg["currency"],
        "metadata": {"package_id": body.package_id},
        "payment_status": "initiated",
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"url": session.url, "session_id": session.session_id}


@api.get("/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    host_url = str(request.base_url)
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)

    status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)

    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable")

    # Idempotency: only update plan once
    if tx["payment_status"] != "paid" and status.payment_status == "paid":
        package_id = tx.get("package_id", "premium_monthly")
        days = 365 if package_id == "premium_yearly" else 30
        expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
        await db.users.update_one(
            {"_id": ObjectId(tx["user_id"])},
            {"$set": {"plan": "premium", "plan_expires_at": expires}},
        )

    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": status.payment_status, "status": status.status}},
    )

    return {
        "session_id": session_id,
        "payment_status": status.payment_status,
        "status": status.status,
        "amount_total": status.amount_total,
        "currency": status.currency,
    }


@api.post("/webhook/stripe")
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
            await db.users.update_one(
                {"_id": ObjectId(tx["user_id"])},
                {"$set": {"plan": "premium", "plan_expires_at": expires}},
            )
            await db.payment_transactions.update_one(
                {"session_id": evt.session_id},
                {"$set": {"payment_status": "paid", "status": "complete"}},
            )
    return {"ok": True}


@api.get("/packages")
async def list_packages():
    return [
        {"id": pid, **{k: v for k, v in pkg.items()}} for pid, pkg in PACKAGES.items()
    ]


# ---------------------------------------------------------------------------
# Défi Famille (Challenges)
# ---------------------------------------------------------------------------
class ChallengeCreate(BaseModel):
    category_id: str
    num_questions: int = Field(5, ge=3, le=10)


class ChallengeParticipate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    answers: List[int]
    duration_seconds: Optional[int] = None


def _public_challenge(doc: dict, include_correct: bool = False) -> dict:
    """Build a JSON-safe challenge payload. By default, hides correct_index."""
    qs = []
    for q in doc.get("questions", []):
        item = {
            "id": q["id"],
            "question": q["question"],
            "options": q["options"],
        }
        if include_correct:
            item["correct_index"] = q["correct_index"]
            item["explanation"] = q.get("explanation", "")
        qs.append(item)
    return {
        "token": doc["token"],
        "category_id": doc["category_id"],
        "creator_name": doc["creator_name"],
        "questions": qs,
        "total": len(qs),
        "participants": sorted(
            doc.get("participants", []),
            key=lambda p: (-p.get("score", 0), p.get("duration_seconds") or 9999),
        ),
        "created_at": doc.get("created_at"),
    }


@api.post("/challenges")
async def create_challenge(body: ChallengeCreate, user: dict = Depends(get_current_user)):
    if user.get("plan") != "premium":
        raise HTTPException(status_code=402, detail="Le Défi Famille est réservé aux membres Premium")
    cat = await db.categories.find_one({"id": body.category_id}, {"_id": 0})
    if not cat:
        raise HTTPException(status_code=404, detail="Catégorie introuvable")
    pool = await db.questions.find({"category_id": body.category_id}, {"_id": 0}).to_list(200)
    if len(pool) < 3:
        raise HTTPException(status_code=400, detail="Pas assez de questions dans cette catégorie")
    import random
    random.shuffle(pool)
    selected = pool[: min(body.num_questions, len(pool))]
    token = secrets.token_urlsafe(8)
    doc = {
        "token": token,
        "creator_user_id": str(user["_id"]),
        "creator_name": user.get("name", "Un proche"),
        "category_id": body.category_id,
        "category_title": cat["title"],
        "category_mascot_image": cat.get("mascot_image"),
        "category_mascot_name": cat.get("mascot_name"),
        "questions": selected,
        "participants": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.challenges.insert_one(doc)
    return {"token": token, "total": len(selected), "category": cat}


@api.get("/challenges/mine")
async def list_my_challenges(user: dict = Depends(get_current_user)):
    rows = await db.challenges.find(
        {"creator_user_id": str(user["_id"])}, {"_id": 0, "questions.correct_index": 0, "questions.explanation": 0}
    ).sort("created_at", -1).to_list(50)
    # Add category metadata + sorted participants summary
    for r in rows:
        r["participants"] = sorted(
            r.get("participants", []),
            key=lambda p: (-p.get("score", 0), p.get("duration_seconds") or 9999),
        )
        r["total_questions"] = len(r.get("questions", []))
    return rows


@api.get("/challenges/{token}")
async def get_challenge(token: str):
    doc = await db.challenges.find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Défi introuvable")
    return {
        **_public_challenge(doc, include_correct=False),
        "category_title": doc.get("category_title"),
        "category_mascot_image": doc.get("category_mascot_image"),
        "category_mascot_name": doc.get("category_mascot_name"),
    }


@api.post("/challenges/{token}/participate")
async def participate_challenge(token: str, body: ChallengeParticipate):
    doc = await db.challenges.find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Défi introuvable")
    qs = doc.get("questions", [])
    if len(body.answers) != len(qs):
        raise HTTPException(status_code=400, detail="Nombre de réponses invalide")
    # Server-side score computation (no trust in client)
    score = 0
    detail = []
    for i, q in enumerate(qs):
        chosen = body.answers[i]
        is_correct = chosen == q["correct_index"]
        if is_correct:
            score += 1
        detail.append({
            "question_id": q["id"],
            "chosen": chosen,
            "correct_index": q["correct_index"],
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })
    participant = {
        "name": body.name.strip()[:40],
        "score": score,
        "total": len(qs),
        "duration_seconds": body.duration_seconds,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.challenges.update_one(
        {"token": token}, {"$push": {"participants": participant}}
    )
    fresh = await db.challenges.find_one({"token": token})
    leaderboard = sorted(
        fresh.get("participants", []),
        key=lambda p: (-p.get("score", 0), p.get("duration_seconds") or 9999),
    )
    return {
        "score": score,
        "total": len(qs),
        "detail": detail,
        "leaderboard": leaderboard,
    }


# ---------------------------------------------------------------------------
# Promo codes (admin-managed, free Premium activation)
# ---------------------------------------------------------------------------
LIFETIME_DAYS = 36500  # ~100 years


class PromoCreate(BaseModel):
    code: Optional[str] = None  # if None → random
    duration_days: int = Field(..., ge=1, le=LIFETIME_DAYS)
    max_uses: Optional[int] = Field(None, ge=1, le=100000)  # None = unlimited
    expires_at: Optional[str] = None  # ISO date string, optional
    label: Optional[str] = Field(None, max_length=120)


class PromoRedeem(BaseModel):
    code: str = Field(min_length=2, max_length=40)


def _promo_to_public(p: dict) -> dict:
    return {
        "id": str(p["_id"]),
        "code": p["code"],
        "label": p.get("label") or "",
        "duration_days": p["duration_days"],
        "max_uses": p.get("max_uses"),
        "used_count": p.get("used_count", 0),
        "redeemed_by": p.get("redeemed_by", []),
        "expires_at": p.get("expires_at"),
        "active": p.get("active", True),
        "created_at": p.get("created_at"),
        "is_lifetime": p["duration_days"] >= LIFETIME_DAYS,
    }


@api.post("/promo/redeem")
async def redeem_promo(body: PromoRedeem, user: dict = Depends(get_current_user)):
    code = body.code.strip().upper()
    promo = await db.promo_codes.find_one({"code": code})
    if not promo or not promo.get("active", True):
        raise HTTPException(status_code=404, detail="Code invalide ou expiré")

    # Expiry check
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

    # Max uses check
    used = promo.get("used_count", 0)
    if promo.get("max_uses") is not None and used >= promo["max_uses"]:
        raise HTTPException(status_code=410, detail="Ce code a atteint sa limite d'utilisations")

    # Prevent same user from redeeming the same code twice
    redeemed_by = promo.get("redeemed_by", [])
    user_id_str = str(user["_id"])
    if user_id_str in redeemed_by:
        raise HTTPException(status_code=400, detail="Vous avez déjà utilisé ce code")

    # Apply premium
    days = int(promo["duration_days"])
    is_lifetime = days >= LIFETIME_DAYS
    expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    await db.users.update_one(
        {"_id": ObjectId(user_id_str)},
        {"$set": {"plan": "premium", "plan_expires_at": expires}},
    )
    await db.promo_codes.update_one(
        {"_id": promo["_id"]},
        {"$inc": {"used_count": 1}, "$push": {"redeemed_by": user_id_str}},
    )

    return {
        "ok": True,
        "plan": "premium",
        "plan_expires_at": expires,
        "is_lifetime": is_lifetime,
        "duration_days": days,
        "label": promo.get("label") or "",
    }


@api.post("/admin/promo")
async def admin_create_promo(body: PromoCreate, admin: dict = Depends(get_admin_user)):
    code = (body.code or secrets.token_urlsafe(6)).strip().upper().replace(" ", "")
    if not code or len(code) < 2:
        raise HTTPException(status_code=400, detail="Code invalide")
    existing = await db.promo_codes.find_one({"code": code})
    if existing:
        raise HTTPException(status_code=400, detail="Ce code existe déjà")
    doc = {
        "code": code,
        "label": (body.label or "").strip() or None,
        "duration_days": int(body.duration_days),
        "max_uses": body.max_uses,
        "expires_at": body.expires_at,
        "used_count": 0,
        "redeemed_by": [],
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": str(admin["_id"]),
    }
    result = await db.promo_codes.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _promo_to_public(doc)


@api.get("/admin/promo")
async def admin_list_promo(admin: dict = Depends(get_admin_user)):
    rows = await db.promo_codes.find().sort("created_at", -1).to_list(500)
    return [_promo_to_public(r) for r in rows]


@api.patch("/admin/promo/{promo_id}")
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


@api.delete("/admin/promo/{promo_id}")
async def admin_delete_promo(promo_id: str, admin: dict = Depends(get_admin_user)):
    try:
        oid = ObjectId(promo_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID invalide")
    result = await db.promo_codes.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Code introuvable")
    return {"ok": True}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup: indexes + seed
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.categories.create_index("id", unique=True)
    await db.questions.create_index("category_id")
    await db.attempts.create_index([("user_id", 1), ("created_at", -1)])
    await db.payment_transactions.create_index("session_id", unique=True)
    await db.challenges.create_index("token", unique=True)
    await db.challenges.create_index([("creator_user_id", 1), ("created_at", -1)])
    await db.promo_codes.create_index("code", unique=True)
    await db.password_reset_tokens.create_index("token", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)

    # Seed categories
    for cat in CATEGORIES:
        await db.categories.update_one({"id": cat["id"]}, {"$set": cat}, upsert=True)

    # Seed questions (clear & reload to keep data fresh on every restart)
    await db.questions.delete_many({})
    if QUESTIONS:
        await db.questions.insert_many([{**q} for q in QUESTIONS])

    # Seed admin
    existing = await db.users.find_one({"email": ADMIN_EMAIL})
    if existing is None:
        await db.users.insert_one({
            "email": ADMIN_EMAIL,
            "password_hash": hash_password(ADMIN_PASSWORD),
            "name": "Administrateur",
            "role": "admin",
            "plan": "premium",
            "plan_expires_at": (datetime.now(timezone.utc) + timedelta(days=3650)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Admin créé : {ADMIN_EMAIL}")
    elif not verify_password(ADMIN_PASSWORD, existing["password_hash"]):
        await db.users.update_one(
            {"email": ADMIN_EMAIL},
            {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}},
        )
        logger.info("Admin password mis à jour")

    # Seed default promo codes (idempotent: only insert if absent)
    default_promos = [
        {
            "code": "FAMILLE2026",
            "label": "Code famille — accès Premium à vie",
            "duration_days": LIFETIME_DAYS,
            "max_uses": None,  # unlimited
            "expires_at": None,
            "active": True,
        },
        {
            "code": "DECOUVERTE30",
            "label": "Essai 30 jours — 50 utilisations",
            "duration_days": 30,
            "max_uses": 50,
            "expires_at": None,
            "active": True,
        },
    ]
    for promo in default_promos:
        if not await db.promo_codes.find_one({"code": promo["code"]}):
            await db.promo_codes.insert_one({
                **promo,
                "used_count": 0,
                "redeemed_by": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": "system",
            })
            logger.info(f"Promo seedé : {promo['code']}")


@app.on_event("shutdown")
async def shutdown():
    client.close()
