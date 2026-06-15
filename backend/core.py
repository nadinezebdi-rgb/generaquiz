"""Shared infrastructure: env, db, models, auth deps, rate-limiter."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Annotated, Any

import bcrypt
import jwt
import resend
from bson import ObjectId
from fastapi import HTTPException, Request, Response, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field, BeforeValidator

# -------------------- env --------------------
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

LIFETIME_DAYS = 36500

# ---------------------------------------------------------------------------
# Gamification economy
# ---------------------------------------------------------------------------
WELCOME_CREDITS = 5          # gift on signup
AD_REWARD_CREDITS = 1        # per rewarded video ad
AD_REWARD_DAILY_CAP = 5      # max rewarded ads / day
CHALLENGE_COMPLETE_CREDITS = 1
HINT_5050_COST = 2
STREAK_SAVER_COST = 10

# XP rewards (used by ladder/leagues weekly ranking)
XP_PER_CORRECT_DAILY = 10        # each correct answer in /daily/submit
XP_PER_CORRECT_CATEGORY = 1      # each correct answer in a category quiz
XP_CHALLENGE_COMPLETION = 50     # finishing a family challenge

LEAGUES = ["bronze", "argent", "or", "diamant"]
LEAGUE_COHORT_SIZE = 30
LEAGUE_PROMOTE = 5  # top 5 promote each Sunday
LEAGUE_RELEGATE = 3  # bottom 3 relegate

PACKAGES = {
    "premium_monthly": {"amount": 9.99, "currency": "eur", "label": "Premium Mensuel",
                        "description": "Accès illimité aux quiz, activités et défis famille"},
    "premium_yearly": {"amount": 89.99, "currency": "eur", "label": "Premium Annuel",
                       "description": "12 mois — économisez 2 mois"},
}

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("quizdantan")


# -------------------- helpers --------------------
def _oid(v: Any) -> str:
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
    return jwt.encode({"sub": user_id, "email": email, "type": "access",
                       "exp": datetime.now(timezone.utc) + timedelta(days=7)},
                      JWT_SECRET, algorithm=JWT_ALG)


def create_refresh_token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "type": "refresh",
                       "exp": datetime.now(timezone.utc) + timedelta(days=30)},
                      JWT_SECRET, algorithm=JWT_ALG)


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie("access_token", access, httponly=True, secure=True, samesite="none",
                        max_age=7 * 24 * 3600, path="/")
    response.set_cookie("refresh_token", refresh, httponly=True, secure=True, samesite="none",
                        max_age=30 * 24 * 3600, path="/")


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def user_to_public(u: dict) -> dict:
    return {"id": str(u["_id"]), "email": u["email"], "name": u.get("name", ""),
            "role": u.get("role", "user"), "plan": u.get("plan", "free"),
            "plan_expires_at": u.get("plan_expires_at"), "created_at": u.get("created_at"),
            "streak_current": int(u.get("streak_current") or 0),
            "streak_best": int(u.get("streak_best") or 0),
            "streak_last_date": u.get("streak_last_date"),
            "daily_email_optin": u.get("daily_email_optin", True),
            "credits": int(u.get("credits") or 0),
            "xp_total": int(u.get("xp_total") or 0),
            "auth_provider": u.get("auth_provider", "email")}


# -------------------- auth dependencies --------------------
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
        return dict(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expirée")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")


async def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès administrateur requis")
    return user


# -------------------- rate limiter (in-memory, IP-based) --------------------
_rate_buckets: dict[str, list[float]] = {}


def rate_limit(prefix: str, max_calls: int, window_seconds: int):
    """Dependency that throttles by client IP. Raises 429 when over budget."""
    async def _checker(request: Request):
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "anon")
        ip = ip.split(",")[0].strip()
        key = f"{prefix}:{ip}"
        now = time.time()
        bucket = _rate_buckets.get(key, [])
        # keep only timestamps inside the window
        bucket = [t for t in bucket if now - t < window_seconds]
        if len(bucket) >= max_calls:
            retry_after = int(window_seconds - (now - bucket[0]))
            raise HTTPException(
                status_code=429,
                detail=f"Trop de tentatives. Réessayez dans {max(retry_after, 1)} s.",
                headers={"Retry-After": str(max(retry_after, 1))},
            )
        bucket.append(now)
        _rate_buckets[key] = bucket
    return _checker


# -------------------- shared Pydantic models --------------------
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


class DailyEmailPrefRequest(BaseModel):
    daily_email_optin: bool


class AttemptCreate(BaseModel):
    category_id: str
    score: int
    total: int
    duration_seconds: Optional[int] = None


class CheckoutCreate(BaseModel):
    package_id: str
    origin_url: str


class ChallengeCreate(BaseModel):
    category_id: str
    num_questions: int = Field(5, ge=3, le=10)


class ChallengeParticipate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    answers: list[int]
    duration_seconds: Optional[int] = None


class PromoCreate(BaseModel):
    code: Optional[str] = None
    duration_days: int = Field(..., ge=1, le=LIFETIME_DAYS)
    max_uses: Optional[int] = Field(None, ge=1, le=100000)
    expires_at: Optional[str] = None
    label: Optional[str] = Field(None, max_length=120)


class PromoRedeem(BaseModel):
    code: str = Field(min_length=2, max_length=40)
