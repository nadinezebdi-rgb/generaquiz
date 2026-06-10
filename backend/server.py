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

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from core import (
    ROOT_DIR, FRONTEND_URL, ADMIN_EMAIL, ADMIN_PASSWORD, LIFETIME_DAYS,
    client, db, logger, hash_password, verify_password,
)
from seed_data import CATEGORIES, QUESTIONS

from routers import auth as auth_router
from routers import quiz as quiz_router
from routers import payments as payments_router
from routers import challenges as challenges_router
from routers import promo as promo_router
from routers import daily as daily_router

app = FastAPI(title="Quiz d'Antan API")
api = APIRouter(prefix="/api")


@api.get("/")
async def root():
    return {"status": "ok", "app": "Quiz d'Antan"}


# Mount routers under /api
api.include_router(auth_router.router)
api.include_router(quiz_router.router)
api.include_router(payments_router.router)
api.include_router(challenges_router.router)
api.include_router(promo_router.router)
api.include_router(daily_router.router)
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
    await db.categories.create_index("id", unique=True)
    await db.questions.create_index("category_id")
    await db.attempts.create_index([("user_id", 1), ("created_at", -1)])
    await db.payment_transactions.create_index("session_id", unique=True)
    await db.challenges.create_index("token", unique=True)
    await db.challenges.create_index([("creator_user_id", 1), ("created_at", -1)])
    await db.promo_codes.create_index("code", unique=True)
    await db.password_reset_tokens.create_index("token", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.daily_attempts.create_index([("user_id", 1), ("date_key", 1)], unique=True)
    await db.daily_attempts.create_index([("date_key", 1), ("score", -1), ("duration_seconds", 1)])

    # Seed categories + questions (refresh on every boot)
    for cat in CATEGORIES:
        await db.categories.update_one({"id": cat["id"]}, {"$set": cat}, upsert=True)
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

    # Seed default promo codes (idempotent)
    default_promos = [
        {"code": "FAMILLE2026", "label": "Code famille — accès Premium à vie",
         "duration_days": LIFETIME_DAYS, "max_uses": None, "expires_at": None, "active": True},
        {"code": "DECOUVERTE30", "label": "Essai 30 jours — 50 utilisations",
         "duration_days": 30, "max_uses": 50, "expires_at": None, "active": True},
    ]
    for promo in default_promos:
        if not await db.promo_codes.find_one({"code": promo["code"]}):
            await db.promo_codes.insert_one({**promo, "used_count": 0, "redeemed_by": [],
                                             "created_at": datetime.now(timezone.utc).isoformat(),
                                             "created_by": "system"})
            logger.info(f"Promo seedé : {promo['code']}")


@app.on_event("shutdown")
async def shutdown():
    client.close()
