"""Quiz d'Antan SaaS — FastAPI orchestrator.

Modular structure:
- core.py: env, db, models, helpers, dependencies, rate-limiter
- routers/auth.py: authentication & account management
- routers/quiz.py: catalog, questions, attempts, stats
- routers/payments.py: Stripe checkout & webhook
- routers/challenges.py: Défi Famille
- routers/promo.py: promo codes (user redeem + admin CRUD)
"""
from datetime import datetime, timezone, timedelta
import asyncio

from fastapi import APIRouter, Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from core import (
    ROOT_DIR, FRONTEND_URL, ADMIN_EMAIL, ADMIN_PASSWORD,
    client, db, logger, hash_password, verify_password, get_admin_user,
)
from seed_data import CATEGORIES, QUESTIONS
from daily_email import start_daily_scheduler, stop_daily_scheduler, send_morning_emails
from mistral_client import regenerate_all as mistral_regenerate_all

from routers import auth as auth_router
from routers import social_auth as social_auth_router
from routers import quiz as quiz_router
from routers import payments as payments_router
from routers import challenges as challenges_router
from routers import promo as promo_router
from routers import daily as daily_router
from routers import gamification as gamification_router
from routers import reports as reports_router
from routers import stats as stats_router
from routers import referral as referral_router
from routers import coop_challenges as coop_challenges_router
from routers import progression as progression_router
from routers.referral import generate_referral_code_for

app = FastAPI(title="Quiz d'Antan API")
api = APIRouter(prefix="/api")


@api.get("/")
async def root():
    return {"status": "ok", "app": "Quiz d'Antan"}


@api.post("/admin/daily-email/trigger")
async def admin_trigger_daily_email(user: dict = Depends(get_admin_user)):
    """Admin-only manual trigger for the morning email (used for testing and recovery)."""
    return await send_morning_emails()


@api.post("/admin/mistral/regenerate")
async def admin_mistral_regenerate(user: dict = Depends(get_admin_user)):
    """Admin-only manual trigger for the full Mistral regeneration of all 800 questions.

    The job is kicked off as a background task and returns immediately
    (full regeneration takes ~3-5 minutes — too long for an HTTP request).
    Watch the server logs (`[mistral] ...`) to track progress.
    """
    asyncio.create_task(mistral_regenerate_all())
    return {
        "ok": True,
        "message": "Régénération Mistral lancée en arrière-plan (~3-5 min). Consultez les logs serveur.",
    }


@api.get("/admin/mistral/ping")
async def admin_mistral_ping(user: dict = Depends(get_admin_user)):
    """Admin-only healthcheck for the Mistral integration.

    Returns OK/KO + latency, the last regeneration summary, and the current
    questions-per-category counts. Use this to spot a rotated key or a stale
    category before the user reports it.
    """
    from mistral_client import ping as mistral_ping
    return await mistral_ping()


# Mount routers under /api
api.include_router(auth_router.router)
api.include_router(social_auth_router.router)
api.include_router(quiz_router.router)
api.include_router(payments_router.router)
api.include_router(challenges_router.router)
api.include_router(promo_router.router)
api.include_router(daily_router.router)
api.include_router(gamification_router.router)
api.include_router(reports_router.router)
api.include_router(stats_router.router)
api.include_router(referral_router.router)
api.include_router(coop_challenges_router.router)
api.include_router(progression_router.router)
app.include_router(api)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static (served at /api/static so it goes through the ingress)
STATIC_DIR = ROOT_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "mascots").mkdir(exist_ok=True)
app.mount("/api/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
async def startup():
    # Indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("apple_sub", sparse=True)
    await db.users.create_index("google_sub", sparse=True)
    await db.categories.create_index("id", unique=True)
    await db.questions.create_index("category_id")
    # Composite index for the security lookup in POST /attempts
    # (fetches questions by their id list restricted to the category)
    await db.questions.create_index([("id", 1), ("category_id", 1)])
    await db.attempts.create_index([("user_id", 1), ("created_at", -1)])
    await db.payment_transactions.create_index("session_id", unique=True)
    await db.challenges.create_index("token", unique=True)
    await db.challenges.create_index([("creator_user_id", 1), ("created_at", -1)])
    await db.promo_codes.create_index("code", unique=True)
    await db.password_reset_tokens.create_index("token", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.daily_attempts.create_index([("user_id", 1), ("date_key", 1)], unique=True)
    await db.daily_attempts.create_index([("date_key", 1), ("score", -1), ("duration_seconds", 1)])
    # Gamification indexes
    await db.credit_ledger.create_index([("user_id", 1), ("created_at", -1)])
    await db.league_memberships.create_index([("user_id", 1), ("week_key", 1)], unique=True)
    await db.league_memberships.create_index("cohort_id")
    await db.league_scores.create_index([("user_id", 1), ("week_key", 1)], unique=True)
    await db.league_scores.create_index([("week_key", 1), ("xp", -1)])
    await db.question_reports.create_index([("status", 1), ("question_id", 1)])
    await db.question_reports.create_index([("user_id", 1), ("question_id", 1)])
    # Referral indexes (unique sparse: users created before P2 have no code yet)
    await db.users.create_index("referral_code", unique=True, sparse=True)
    # App-wide state (e.g. Mistral last regen) — single doc keyed by `key`
    await db.app_state.create_index("key", unique=True)
    # Cooperative challenges — token lookup + creator listing
    await db.coop_challenges.create_index("token", unique=True)
    await db.coop_challenges.create_index([("creator_user_id", 1), ("created_at", -1)])
    # Badges — one row per (user, badge) with unique index for idempotent inserts
    await db.user_badges.create_index([("user_id", 1), ("badge_id", 1)], unique=True)
    # Category mastery — one row per (user, category)
    await db.user_category_stats.create_index([("user_id", 1), ("category_id", 1)], unique=True)

    # Seed categories (always refresh metadata: title/description/mascot/count)
    for cat in CATEGORIES:
        await db.categories.update_one({"id": cat["id"]}, {"$set": cat}, upsert=True)

    # Seed questions ONLY if the pool is empty (first boot or after manual flush).
    # Mistral regenerates the full pool nightly at 03:00 Paris — we don't want
    # to overwrite those fresh questions on every container restart.
    existing_q = await db.questions.estimated_document_count()
    if existing_q == 0:
        if QUESTIONS:
            await db.questions.insert_many([{**q} for q in QUESTIONS])
            logger.info(f"Pool de questions vide : {len(QUESTIONS)} questions seed insérées")
    else:
        logger.info(f"{existing_q} questions déjà en DB — seed sauté (Mistral gère la régénération)")

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

    # Backfill credits for users registered before the credits system.
    # Idempotent: only acts on users missing the `credits` field.
    backfilled = await db.users.update_many(
        {"credits": {"$exists": False}},
        {"$set": {"credits": 5, "xp_total": 0}},
    )
    if backfilled.modified_count:
        logger.info(f"Crédits de bienvenue rétroactifs : {backfilled.modified_count} utilisateurs")

    # Backfill referral_code for legacy users (one-time, idempotent — runs once per user).
    legacy_users = db.users.find(
        {"referral_code": {"$exists": False}},
        {"_id": 1, "name": 1, "email": 1},
    )
    backfill_count = 0
    async for u in legacy_users:
        code = await generate_referral_code_for(u.get("name", ""), u.get("email", ""))
        await db.users.update_one(
            {"_id": u["_id"]},
            {"$set": {"referral_code": code, "referral_count": 0}},
        )
        backfill_count += 1
    if backfill_count:
        logger.info(f"Codes parrainage rétroactifs : {backfill_count} utilisateurs")

    # Seed default promo codes (idempotent)
    # Note: les codes "à vie" (FAMILLE2026) ne sont plus seedés par défaut en prod.
    # L'admin peut toujours les créer manuellement via /api/promo/create si besoin.
    default_promos = [
        {"code": "DECOUVERTE30", "label": "Essai 30 jours — 50 utilisations",
         "duration_days": 30, "max_uses": 50, "expires_at": None, "active": True},
    ]
    # Désactiver le code FAMILLE2026 historique s'il est encore actif en base
    await db.promo_codes.update_many(
        {"code": "FAMILLE2026", "active": True},
        {"$set": {"active": False}},
    )
    for promo in default_promos:
        if not await db.promo_codes.find_one({"code": promo["code"]}):
            await db.promo_codes.insert_one({**promo, "used_count": 0, "redeemed_by": [],
                                             "created_at": datetime.now(timezone.utc).isoformat(),
                                             "created_by": "system"})
            logger.info(f"Promo seedé : {promo['code']}")

    # Schedule morning Quiz du Jour reminder emails (09:00 Europe/Paris)
    start_daily_scheduler()


@app.on_event("shutdown")
async def shutdown():
    stop_daily_scheduler()
    client.close()
