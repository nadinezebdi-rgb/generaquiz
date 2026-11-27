"""Shared infrastructure: env, db, models, auth deps, rate-limiter."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import logging
import ipaddress
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Annotated, Any, List

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
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")     # requis pour seeder l'admin, sans valeur par défaut
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")  # requis (aucune valeur en dur)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
GIFT_STRIPE_MODE = os.environ.get("GIFT_STRIPE_MODE", "test").lower()
GIFT_STRIPE_TEST_SECRET_KEY = os.environ.get("GIFT_STRIPE_TEST_SECRET_KEY", "")
GIFT_STRIPE_LIVE_SECRET_KEY = os.environ.get("GIFT_STRIPE_LIVE_SECRET_KEY", "")
GIFT_STRIPE_TEST_WEBHOOK_SECRET = os.environ.get("GIFT_STRIPE_TEST_WEBHOOK_SECRET", "")
GIFT_STRIPE_LIVE_WEBHOOK_SECRET = os.environ.get("GIFT_STRIPE_LIVE_WEBHOOK_SECRET", "")
GIFT_STRIPE_TEST_PRODUCT_ID = os.environ.get("GIFT_STRIPE_TEST_PRODUCT_ID", "")
GIFT_STRIPE_LIVE_PRODUCT_ID = os.environ.get("GIFT_STRIPE_LIVE_PRODUCT_ID", "")
GIFT_STRIPE_TEST_PRICE_ID = os.environ.get("GIFT_STRIPE_TEST_PRICE_ID", "")
GIFT_STRIPE_LIVE_PRICE_ID = os.environ.get("GIFT_STRIPE_LIVE_PRICE_ID", "")
GIFT_CODE_ENCRYPTION_KEY = os.environ.get("GIFT_CODE_ENCRYPTION_KEY", "")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "GénéraQuiz <contact@generaquiz.fr>")

# Garde-fou : si la variable d'environnement n'utilise pas le domaine vérifié,
# on bascule automatiquement sur contact@generaquiz.fr pour éviter le rejet Resend.
# (logger n'est pas encore initialisé ici — on utilise logging.warning directement)
if "@generaquiz.fr" not in SENDER_EMAIL:
    logging.warning(
        f"SENDER_EMAIL='{SENDER_EMAIL}' n'utilise pas le domaine vérifié generaquiz.fr "
        f"— bascule sur contact@generaquiz.fr pour éviter le blocage Resend"
    )
    SENDER_EMAIL = "GénéraQuiz <contact@generaquiz.fr>"

CONTACT_EMAIL = "contact.generaquiz@gmail.com"

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Les réponses des destinataires arrivent sur l'adresse de contact (l'expéditeur reste sur le domaine vérifié).
_resend_send = resend.Emails.send
resend.Emails.send = lambda params, *a, **kw: _resend_send({"reply_to": CONTACT_EMAIL, **params}, *a, **kw)

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
REFERRAL_BONUS_CREDITS = 5   # bonus for BOTH parties when referred user plays 1st quiz

# XP rewards (used by ladder/leagues weekly ranking)
XP_PER_CORRECT_DAILY = 10        # each correct answer in /daily/submit
XP_PER_CORRECT_CATEGORY = 1      # each correct answer in a category quiz
XP_CHALLENGE_COMPLETION = 50     # finishing a family challenge

LEAGUES = ["bronze", "argent", "or", "diamant"]
LEAGUE_COHORT_SIZE = 30
LEAGUE_PROMOTE = 5  # top 5 promote each Sunday
LEAGUE_RELEGATE = 3  # bottom 3 relegate

PACKAGES = {
    # ============ NOUVELLE GRILLE (2026) ============
    # -- Solo : 1 accès personnel complet --
    "solo_monthly":    {"amount": 6.90,  "renew_amount": 6.90, "currency": "eur", "label": "Solo — Mensuel",
                        "tier": "solo",    "period": "monthly",
                        "description": "Quiz illimités, toutes catégories, Livre de Vie PDF"},
    "solo_yearly":     {"amount": 69.00, "renew_amount": 69.00, "currency": "eur", "label": "Solo — Annuel",
                        "tier": "solo",    "period": "yearly",
                        "description": "12 mois — 2 mois offerts par rapport au mensuel"},
    "solo_yearly_noel": {"amount": 49.00, "renew_amount": 69.00, "currency": "eur",
                        "label": "Super promo de Noël Solo", "tier": "solo", "period": "yearly", "promo": True,
                        "description": "49 € pour 12 mois, puis 69 €/an"},
    # -- Famille : bénéficiaire complet + 3 proches dans l'espace famille --
    "famille_v2_monthly": {"amount": 9.90, "renew_amount": 9.90, "currency": "eur", "label": "Famille — Mensuel",
                        "tier": "famille_v2", "period": "monthly",
                        "description": "Tout Solo + 3 proches invités aux quiz, défis et classements familiaux"},
    "famille_v2_yearly":  {"amount": 99.00, "renew_amount": 99.00, "currency": "eur", "label": "Famille — Annuel",
                        "tier": "famille_v2", "period": "yearly",
                        "description": "12 mois — 2 mois offerts par rapport au mensuel"},
    "famille_v2_yearly_noel": {"amount": 79.00, "renew_amount": 99.00, "currency": "eur",
                        "label": "Super promo de Noël Famille", "tier": "famille_v2", "period": "yearly", "promo": True,
                        "description": "79 € pour 12 mois, puis 99 €/an"},
    # -- Héritage : plus vendu (abonnés existants conservés) --
    "heritage_yearly": {"amount": 159.00,"currency": "eur", "label": "Héritage — Annuel",
                        "tier": "heritage", "period": "yearly", "legacy": True,
                        "description": "Ancienne formule (grandfathering)"},
    # -- Cadeaux (paiements uniques, montant fixé par routers/gifts.py) --
    "gift_famille":    {"amount": 79.00, "currency": "eur", "label": "Carte cadeau Famille",
                        "tier": "gift", "period": "one_time",
                        "description": "1 an Famille — carte PDF à imprimer"},
    "gift_solo":       {"amount": 49.00, "currency": "eur", "label": "Carte cadeau Solo",
                        "tier": "gift", "period": "one_time",
                        "description": "1 an Solo — carte PDF à imprimer"},
    "gift_heritage":   {"amount": 159.00,"currency": "eur", "label": "Coffret Héritage",
                        "tier": "gift", "period": "one_time", "legacy": True,
                        "description": "Ancien coffret"},
    "gift_livre":      {"amount": 79.90, "currency": "eur", "label": "Livre de Vie imprimé",
                        "tier": "gift", "period": "one_time", "legacy": True,
                        "description": "1 Livre imprimé A5 — sans abonnement"},
    # ============ ANCIENS PLANS (grandfathering — conservés) ============
    # Les abonnés existants gardent l'accès à ces packages, non affichés en front
    "club_monthly":    {"amount": 4.99,  "currency": "eur", "label": "Club Mémoire — Mensuel",
                        "tier": "club",    "period": "monthly", "legacy": True,
                        "description": "Ancienne formule (grandfathering)"},
    "club_yearly":     {"amount": 49.99, "currency": "eur", "label": "Club Mémoire — Annuel",
                        "tier": "club",    "period": "yearly", "legacy": True,
                        "description": "Ancienne formule (grandfathering)"},
    "famille_monthly": {"amount": 7.99,  "currency": "eur", "label": "Famille — Mensuel (ancienne)",
                        "tier": "famille", "period": "monthly", "legacy": True,
                        "description": "Ancienne formule (grandfathering)"},
    "famille_yearly":  {"amount": 79.99, "currency": "eur", "label": "Famille — Annuel (ancienne)",
                        "tier": "famille", "period": "yearly", "legacy": True,
                        "description": "Ancienne formule (grandfathering)"},
    "premium_monthly": {"amount": 12.99, "currency": "eur", "label": "Premium — Mensuel",
                        "tier": "premium", "period": "monthly", "legacy": True,
                        "description": "Ancienne formule (grandfathering)"},
    "premium_yearly":  {"amount": 129.99,"currency": "eur", "label": "Premium — Annuel",
                        "tier": "premium", "period": "yearly", "legacy": True,
                        "description": "Ancienne formule (grandfathering)"},
}

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("quizdantan")
# Uvicorn peut re-configurer le root logger au niveau WARNING → on force INFO
# explicitement sur notre logger pour garantir la visibilité des logs de seed
# et autres diagnostics de démarrage.
logger.setLevel(logging.INFO)


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


def create_access_token(user_id: str, email: str, token_version: int = 0) -> str:
    return jwt.encode({"sub": user_id, "email": email, "type": "access", "tv": token_version,
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


def _age_group(birth_year: Optional[int]) -> Optional[str]:
    """Map birth_year → "jeune" (≤25), "senior" (≥55), "libre" (between).

    Returns None if birth_year not set. Used only as a hint for the
    cooperative challenge UI — never gates features."""
    if not birth_year:
        return None
    now_year = datetime.now(timezone.utc).year
    age = now_year - birth_year
    if age <= 25:
        return "jeune"
    if age >= 55:
        return "senior"
    return "libre"


def is_premium_active(u: dict) -> bool:
    """True si l'utilisateur a un plan Premium ENCORE actif (non expiré).
    Prend en charge plan_expires_at absent (lifetime) et passé (expiré).
    Utilisé par les gates de features Premium pour éviter que les comptes
    expirés continuent d'avoir accès aux quotas / features premium.
    """
    if u.get("plan") != "premium":
        return False
    exp_raw = u.get("plan_expires_at")
    if not exp_raw:
        return True  # pas de date → considéré lifetime
    try:
        exp = datetime.fromisoformat(exp_raw)
        return exp >= datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return True  # date illisible → fail open pour ne pas priver un client payant


def user_to_public(u: dict) -> dict:
    # Compute level info from xp_total for the client badges/progress ring.
    # Lazy import to avoid circular ref.
    try:
        from progression import compute_level
        level_info = compute_level(int(u.get("xp_total") or 0))
    except Exception:
        level_info = {"level": 1, "progress_pct": 0, "xp_to_next": 50, "next_level_at": 50, "xp_in_level": 0}

    # Normalise le plan : si plan_expires_at est passé, on renvoie "free".
    # Ainsi le frontend et tout consommateur de /me voient un état cohérent
    # même si le champ `plan` en base n'a pas encore été rétrogradé.
    plan = u.get("plan", "free")
    plan_expires_at = u.get("plan_expires_at")
    if plan == "premium" and plan_expires_at:
        try:
            exp = datetime.fromisoformat(plan_expires_at)
            if exp < datetime.now(timezone.utc):
                plan = "free"  # abonnement expiré
        except (ValueError, TypeError):
            pass

    return {"id": str(u["_id"]), "email": u["email"], "name": u.get("name", ""),
            "role": u.get("role", "user"), "plan": plan,
            "plan_expires_at": plan_expires_at, "created_at": u.get("created_at"),
            "plan_tier": u.get("plan_tier"),          # "club" | "famille" | "premium" | None
            "plan_period": u.get("plan_period"),      # "monthly" | "yearly" | None
            "email_verified": bool(u.get("email_verified")),
            "plan_renews_at": u.get("plan_renews_at"), "plan_auto_renew": bool(u.get("plan_auto_renew")),
            "plan_cancel_at_period_end": bool(u.get("plan_cancel_at_period_end")),
            "plan_renewal_amount": u.get("plan_renewal_amount"), "plan_package_id": u.get("plan_package_id"),
            "streak_current": int(u.get("streak_current") or 0),
            "streak_best": int(u.get("streak_best") or 0),
            "streak_last_date": u.get("streak_last_date"),
            "daily_email_optin": u.get("daily_email_optin", True),
            "credits": int(u.get("credits") or 0),
            "xp_total": int(u.get("xp_total") or 0),
            "level": level_info["level"],
            "level_progress_pct": level_info["progress_pct"],
            "xp_to_next_level": level_info["xp_to_next"],
            "referral_code": u.get("referral_code"),
            "referral_count": int(u.get("referral_count") or 0),
            "birth_year": u.get("birth_year"),
            "age_group": _age_group(u.get("birth_year")),
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
        if payload.get("tv", 0) != user.get("token_version", 0):
            raise HTTPException(status_code=401, detail="Session expirée")
        return dict(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expirée")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")


async def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    # superadmin est un admin renforcé — il passe le guard admin
    if user.get("role") not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Accès administrateur requis")
    return user


async def get_superadmin_user(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Accès super-administrateur requis")
    return user


# -------------------- audit log --------------------
async def record_audit(admin: dict, action: str, *,
                       target_type: str | None = None,
                       target_id: str | None = None,
                       target_label: str | None = None,
                       before: Any = None,
                       after: Any = None,
                       meta: dict | None = None) -> None:
    """Trace une action admin sensible dans admin_audit_log.

    Never raises — l'audit ne doit jamais bloquer l'action fonctionnelle.
    """
    try:
        await db.admin_audit_log.insert_one({
            "id": str(ObjectId()),
            "admin_id": str(admin.get("_id")) if admin.get("_id") else None,
            "admin_email": admin.get("email"),
            "admin_role": admin.get("role"),
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "target_label": target_label,
            "before": before,
            "after": after,
            "meta": meta or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"audit log failed for action={action}: {e}")


# -------------------- rate limiter (in-memory, IP-based) --------------------


_CLOUDFLARE_NETS = [ipaddress.ip_network(n) for n in (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "141.101.64.0/18",
    "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17",
    "162.158.0.0/15", "104.16.0.0/13", "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32", "2405:8100::/32",
    "2a06:98c0::/29", "2c0f:f248::/32")]


def _is_proxy(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private or any(addr in n for n in _CLOUDFLARE_NETS)


def client_ip(request: Request) -> str:
    """IP réelle : X-Forwarded-For lu de droite à gauche, en sautant notre répartiteur et les relais Cloudflare.
    Les entrées les plus à gauche (écrites par le client) ne sont jamais utilisées."""
    hops = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    for ip in reversed(hops[:-1]):  # la dernière entrée est l'adresse du répartiteur de charge
        if not _is_proxy(ip):
            return ip
    return hops[0] if len(hops) == 1 else (request.client.host if request.client else "anon")


async def rate_hit(key: str, max_calls: int, window_seconds: int, record: bool = True) -> None:
    """Limiteur partagé entre processus (stocké dans Mongo, purgé par index TTL)."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(seconds=window_seconds)
    used = await db.rate_limits.count_documents({"key": key, "at": {"$gte": since}})
    if used >= max_calls:
        first = await db.rate_limits.find_one({"key": key, "at": {"$gte": since}}, sort=[("at", 1)])
        first_at = first["at"] if first else now
        if first_at.tzinfo is None:
            first_at = first_at.replace(tzinfo=timezone.utc)
        retry = max(int(window_seconds - (now - first_at).total_seconds()), 1)
        minutes = (retry + 59) // 60
        raise HTTPException(status_code=429, headers={"Retry-After": str(retry)},
                            detail=f"Trop de tentatives. Réessayez dans {minutes} minute{'s' if minutes > 1 else ''}.")
    if record:
        await db.rate_limits.insert_one({"key": key, "at": now, "expire_at": now + timedelta(seconds=window_seconds)})


async def rate_record(key: str, window_seconds: int) -> None:
    now = datetime.now(timezone.utc)
    await db.rate_limits.insert_one({"key": key, "at": now, "expire_at": now + timedelta(seconds=window_seconds)})


def rate_limit(prefix: str, max_calls: int, window_seconds: int):
    """Dependency that throttles by real client IP. Raises 429 when over budget."""
    async def _checker(request: Request):
        await rate_hit(f"{prefix}:{client_ip(request)}", max_calls, window_seconds)
    return _checker


# -------------------- shared Pydantic models --------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1, max_length=80)
    referral_code: Optional[str] = Field(None, max_length=40)
    birth_year: Optional[int] = Field(None, ge=1900, le=2026)


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
    birth_year: Optional[int] = Field(None, ge=1900, le=2026)
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None


class DailyEmailPrefRequest(BaseModel):
    daily_email_optin: bool


class AttemptAnswer(BaseModel):
    """Single answer inside a POST /attempts payload — the client sends
    the ORIGINAL question id + the user's picked answer index (0-3).
    The server loads the question and compares to `correct_index` — the
    client's own claim of "score" is IGNORED to prevent cheating."""
    question_id: str = Field(min_length=1, max_length=80)
    answer_index: int = Field(..., ge=0, le=3)


class AttemptCreate(BaseModel):
    category_id: str
    session_id: Optional[str] = None
    answers: List[AttemptAnswer] = Field(..., min_length=1, max_length=30)
    duration_seconds: Optional[int] = Field(None, ge=0, le=7200)


class CheckoutCreate(BaseModel):
    package_id: str
    origin_url: str
    accept_terms: bool = False


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
