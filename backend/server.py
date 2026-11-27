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
from bson import ObjectId
import asyncio
import re

from fastapi import APIRouter, Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from core import (
    ROOT_DIR, FRONTEND_URL, ADMIN_EMAIL, ADMIN_PASSWORD,
    client, db, logger, hash_password, get_admin_user,
)
from seed_data import CATEGORIES, QUESTIONS
from daily_email import send_morning_emails
from scheduler import start_scheduler, stop_scheduler
from mistral_client import regenerate_all as mistral_regenerate_all

from routers import auth as auth_router
from routers import contact as contact_router
import subscription as subscription_mod
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
from routers import atelier as atelier_router
from routers import livre as livre_router
from routers import livre_ai as livre_ai_router
from routers import admin_qa as admin_qa_router
from routers import admin_users as admin_users_router
from routers import admin_audit as admin_audit_router
from routers import palier as palier_router
from routers import palier_weekly as palier_weekly_router
from routers import ehpad as ehpad_router
from routers import admin_analytics as admin_analytics_router
from routers import charades as charades_router
from routers import mots_meles as mots_meles_router
from routers import mots_fleches as mots_fleches_router
from routers import tips as tips_router
from routers import share as share_router
from routers import testimonials as testimonials_router
from routers import site_settings as site_settings_router
from routers import gifts as gifts_router
from routers import family as family_router
from routers import bien_vieillir as bien_vieillir_router
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


@api.get("/admin/users-export")
async def admin_list_users(user: dict = Depends(get_admin_user)):
    """Admin-only: list registered users with email, name, signup date and email opt-in."""
    users = []
    projection = {"email": 1, "name": 1, "role": 1, "plan": 1, "created_at": 1, "daily_email_optin": 1}
    cursor = db.users.find({}, projection).sort("created_at", -1)
    async for u in cursor:
        users.append({
            "email": u.get("email"),
            "name": u.get("name"),
            "role": u.get("role", "user"),
            "plan": u.get("plan", "free"),
            "created_at": u.get("created_at"),
            "daily_email_optin": u.get("daily_email_optin", True),
        })
    return {"count": len(users), "users": users}


# Mount routers under /api
api.include_router(auth_router.router)
api.include_router(contact_router.router)
api.include_router(subscription_mod.router)
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
api.include_router(atelier_router.router)
api.include_router(livre_router.router)
api.include_router(livre_ai_router.router)
api.include_router(admin_qa_router.router)
api.include_router(admin_users_router.router)
api.include_router(admin_audit_router.router)
api.include_router(palier_router.router)
api.include_router(palier_weekly_router.router)
api.include_router(ehpad_router.router)
api.include_router(admin_analytics_router.router)
api.include_router(charades_router.router)
api.include_router(mots_meles_router.router)
api.include_router(mots_fleches_router.router)
api.include_router(tips_router.router)
api.include_router(share_router.router)
api.include_router(testimonials_router.router)
api.include_router(site_settings_router.router)
api.include_router(gifts_router.router)
api.include_router(family_router.router)
api.include_router(bien_vieillir_router.router)
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


async def _safe_index(coll, keys, **kw):
    """Crée un index sans jamais bloquer le démarrage (conflit d'options → drop + recréation)."""
    from pymongo.errors import OperationFailure
    try:
        await coll.create_index(keys, **kw)
    except OperationFailure as e:
        if e.code not in (85, 86):
            logger.error(f"[index] {coll.name} {keys} non créé : {e}")
            return
        name = kw.get("name") or "_".join(f"{k}_{d}" for k, d in ([(keys, 1)] if isinstance(keys, str) else keys))
        try:
            await coll.drop_index(name)
            await coll.create_index(keys, **kw)
            logger.info(f"[index] {coll.name}.{name} recréé")
        except Exception as e2:
            logger.error(f"[index] {coll.name}.{name} non recréé : {e2}")
    except Exception as e:
        logger.error(f"[index] {coll.name} {keys} non créé : {e}")


async def revoke_famille2026():
    """Audit sécurité : le code public FAMILLE2026 (Premium à vie) est désactivé et son Premium retiré, une seule fois."""
    marker = "revoke_famille2026"
    if await db.migrations.find_one({"id": marker}):
        return
    await db.promo_codes.update_one({"code": "FAMILLE2026"}, {"$set": {"active": False, "max_uses": 0}})
    promo = await db.promo_codes.find_one({"code": "FAMILLE2026"}) or {}
    ids = [ObjectId(i) for i in promo.get("redeemed_by", []) if ObjectId.is_valid(i)]
    lifetime_floor = (datetime.now(timezone.utc) + timedelta(days=365 * 20)).isoformat()
    revoked = await db.users.update_many(
        {"_id": {"$in": ids}, "role": {"$nin": ["admin", "superadmin"]}, "plan_auto_renew": {"$ne": True},
         "plan_expires_at": {"$gte": lifetime_floor}},
        {"$set": {"plan": "free", "plan_expires_at": None, "plan_revoked_reason": "FAMILLE2026"}})
    await db.migrations.insert_one({"id": marker, "at": datetime.now(timezone.utc).isoformat(),
                                    "redeemed": len(ids), "revoked": revoked.modified_count})
    logger.warning(f"[securite] FAMILLE2026 désactivé : {len(ids)} utilisation(s), {revoked.modified_count} Premium retiré(s)")


CURATED_DIR = ROOT_DIR / "data" / "curated_questions"


async def sync_curated_questions():
    """Recopie (upsert par id) les questions générées et vérifiées en aperçu, pour que la prod ait les mêmes."""
    import json as _json
    for f in sorted(CURATED_DIR.glob("*.json")):
        docs = _json.loads(f.read_text(encoding="utf-8"))
        for d in docs:
            await db.questions.update_one({"id": d["id"]}, {"$set": d}, upsert=True)
        logger.info(f"[curated] {f.stem} : {len(docs)} question(s) synchronisée(s)")


@app.on_event("startup")
async def startup():
    # Indexes
    await _safe_index(db.users, "email", unique=True)
    await _safe_index(db.rate_limits, [("key", 1), ("at", 1)])
    await _safe_index(db.rate_limits, "expire_at", expireAfterSeconds=0)
    await _safe_index(db.users, "apple_sub", sparse=True)
    await _safe_index(db.users, "google_sub", sparse=True)
    await _safe_index(db.categories, "id", unique=True)
    await _safe_index(db.questions, "category_id")
    # Composite index for the security lookup in POST /attempts
    # (fetches questions by their id list restricted to the category)
    await _safe_index(db.questions, [("id", 1), ("category_id", 1)])
    await _safe_index(db.attempts, [("user_id", 1), ("created_at", -1)])
    await _safe_index(db.payment_transactions, "session_id", unique=True)
    await _safe_index(db.challenges, "token", unique=True)
    await _safe_index(db.challenges, [("creator_user_id", 1), ("created_at", -1)])
    await _safe_index(db.promo_codes, "code", unique=True)
    await gifts_router.ensure_gift_indexes()
    await _safe_index(db.family_proches, "token", unique=True)
    await _safe_index(db.family_proches, [("owner_id", 1), ("status", 1)])

    # -- QA jobs sweep — au startup, TOUS les jobs "running" sont zombies
    # (leur PID a été tué par le restart et peut avoir été réattribué). On
    # les passe inconditionnellement à "failed" AVANT tout test PID.
    from routers.admin_qa import (
        sweep_running_jobs_on_startup,
        _dequeue_next,
        qa_watchdog_loop,
    )
    await sweep_running_jobs_on_startup()
    # Puis on dépile les jobs restés "queued" avant le restart — sinon ils
    # attendent indéfiniment qu'un running (qui n'existe plus) finisse.
    import asyncio as _asyncio
    _asyncio.create_task(_dequeue_next())
    # Watchdog : reprend les jobs orphelins (heartbeat mort) depuis leur checkpoint
    _asyncio.create_task(qa_watchdog_loop())
    await _safe_index(db.password_reset_tokens, "token", unique=True)
    await _safe_index(db.password_reset_tokens, "expires_at", expireAfterSeconds=0)
    await _safe_index(db.daily_attempts, [("user_id", 1), ("date_key", 1)], unique=True)
    await _safe_index(db.daily_quizzes, "date_key", unique=True)
    await _safe_index(db.attempts, 
        [("user_id", 1), ("source", 1), ("category_id", 1), ("mini_week", 1)],
        unique=True, partialFilterExpression={"source": "mini_quiz"}, name="uniq_mini_quiz_claim",
    )
    await _safe_index(db.daily_attempts, [("date_key", 1), ("score", -1), ("duration_seconds", 1)])
    # Gamification indexes
    await _safe_index(db.credit_ledger, [("user_id", 1), ("created_at", -1)])
    await _safe_index(db.league_memberships, [("user_id", 1), ("week_key", 1)], unique=True)
    await _safe_index(db.league_memberships, "cohort_id")
    await _safe_index(db.league_scores, [("user_id", 1), ("week_key", 1)], unique=True)
    await _safe_index(db.league_scores, [("week_key", 1), ("xp", -1)])
    await _safe_index(db.question_reports, [("status", 1), ("question_id", 1)])
    await _safe_index(db.question_reports, [("user_id", 1), ("question_id", 1)])
    # Referral indexes (unique sparse: users created before P2 have no code yet)
    await _safe_index(db.users, "referral_code", unique=True, sparse=True)
    # App-wide state (e.g. Mistral last regen) — single doc keyed by `key`
    await _safe_index(db.app_state, "key", unique=True)
    # Cooperative challenges — token lookup + creator listing
    await _safe_index(db.coop_challenges, "token", unique=True)
    await _safe_index(db.coop_challenges, [("creator_user_id", 1), ("created_at", -1)])
    # Badges — one row per (user, badge) with unique index for idempotent inserts
    await _safe_index(db.user_badges, [("user_id", 1), ("badge_id", 1)], unique=True)
    # Category mastery — one row per (user, category)
    await _safe_index(db.user_category_stats, [("user_id", 1), ("category_id", 1)], unique=True)
    await _safe_index(db.palier_attempts, [("user_id", 1), ("category_id", 1), ("palier", 1)])
    from routers.palier import backfill_legacy_palier_attempts
    logger.info(f"[palier] tentatives historiques reconstituées : {await backfill_legacy_palier_attempts()}")
    await sync_curated_questions()

    # Seed categories (always refresh metadata: title/description/mascot/count/group/sort_order)
    for cat in CATEGORIES:
        await db.categories.update_one({"id": cat["id"]}, {"$set": cat}, upsert=True)
        # Titres recopiés dans les défis : alignés sur le titre courant (affichage uniquement)
        for coll in (db.challenges, db.coop_challenges, db.weekly_palier_challenges):
            await coll.update_many({"category_id": cat["id"], "category_title": {"$ne": cat["title"]}},
                                   {"$set": {"category_title": cat["title"]}})

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

    # Force-seed pour les catégories récemment ajoutées (idempotent). Chaque
    # nouvelle catégorie ajoutée à CATEGORIES qui n'a AUCUNE question en base
    # reçoit ses questions seed pour ne pas attendre le prochain job Mistral.
    for cat in CATEGORIES:
        n = await db.questions.count_documents({"category_id": cat["id"]})
        if n == 0:
            cat_qs = [q for q in QUESTIONS if q["category_id"] == cat["id"]]
            if cat_qs:
                await db.questions.insert_many([{**q} for q in cat_qs])
                logger.info(f"[seed] catégorie '{cat['id']}' vide → {len(cat_qs)} questions seed insérées")

    # Questions seed « Bien vieillir » réécrites (aucune allégation médicale) :
    # on met à jour les anciennes versions et on les renvoie au contrôle IA.
    from seed_data import BIEN_VIEILLIR_QUESTIONS
    for q in BIEN_VIEILLIR_QUESTIONS:
        r = await db.questions.update_one(
            {"id": q["id"], "$or": [{"question": {"$ne": q["question"]}}, {"explanation": {"$ne": q["explanation"]}}]},
            {"$set": {k: q[k] for k in ("question", "options", "correct_index", "explanation", "discussion_prompt") if k in q},
             "$unset": {"quality": "", "fact_check": ""}},
        )
        if r.modified_count:
            logger.info(f"[seed] question {q['id']} (bien-vieillir) mise à jour")

    # Enrichit les questions existantes avec des relances de conversation EHPAD
    from discussion_prompts import enrich_existing_questions
    await enrich_existing_questions()

    # Migration douce des anciens chapitres Livre → nouveaux (10 → 12 chapitres)
    from routers.livre import _migrate_legacy_chapters
    await _migrate_legacy_chapters()

    # ============ Grandfathering : mapping des anciens plan_tier → nouveaux ============
    # Les abonnés existants voient leur plan_tier réétiqueté :
    #   club     → solo         (garde leur ancien prix Stripe)
    #   famille  → famille_v2   (garde leur ancien prix Stripe)
    #   premium  → heritage     (garde leur ancien prix Stripe)
    # L'abonnement Stripe reste sur l'ancien package (`club_monthly` etc.), donc
    # personne ne subit une hausse à la reconduction. Le nouveau `plan_tier`
    # permet uniquement d'unifier l'affichage/permissions côté app.
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: F401
    for old, new in [("club", "solo"), ("famille", "famille_v2"), ("premium", "heritage")]:
        r = await db.users.update_many(
            {"plan_tier": old, "grandfathered": {"$ne": True}},
            {"$set": {"plan_tier": new, "grandfathered": True, "grandfathered_from": old}},
        )
        if r.modified_count:
            logger.info(f"[grandfathering] {old}→{new}: {r.modified_count} utilisateurs")

    # ------------------------------------------------------------------
    # Seed super-admin — IDEMPOTENT à chaque démarrage.
    #   - Si ADMIN_EMAIL n'est pas défini : on ne fait rien (log warning).
    #   - Sinon on cherche le compte par email (comparaison INSENSIBLE à la casse) :
    #       * Introuvable  → on le crée avec role=superadmin (nécessite ADMIN_PASSWORD).
    #       * Trouvé       → on FORCE role=superadmin via update (sans jamais
    #                        toucher au mot de passe existant).
    #   - Chaque branche loggue explicitement ce qu'elle a fait.
    # ------------------------------------------------------------------
    if not ADMIN_EMAIL:
        logger.warning("[seed-admin] ADMIN_EMAIL non défini → seed admin IGNORÉ")
    else:
        admin_email_norm = ADMIN_EMAIL.strip().lower()
        # Comparaison insensible à la casse pour ratrapper les comptes créés en
        # mixed-case avant que l'app normalise à l'inscription.
        existing = await db.users.find_one(
            {"email": {"$regex": f"^{re.escape(admin_email_norm)}$", "$options": "i"}}
        )
        if existing is None:
            if not ADMIN_PASSWORD:
                logger.error(
                    f"[seed-admin] Compte {admin_email_norm} INTROUVABLE et ADMIN_PASSWORD "
                    f"non défini → impossible de créer l'admin. Définissez ADMIN_PASSWORD "
                    f"ou créez le compte manuellement puis relancez le seed."
                )
            else:
                await db.users.insert_one({
                    "email": admin_email_norm,
                    "password_hash": hash_password(ADMIN_PASSWORD),
                    "name": "Administrateur",
                    "role": "superadmin",
                    "plan": "premium",
                    "plan_tier": "premium",
                    "plan_period": "yearly",
                    "plan_expires_at": (datetime.now(timezone.utc) + timedelta(days=3650)).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                logger.info(f"[seed-admin] CRÉÉ : {admin_email_norm} → role=superadmin")
        else:
            # Compte existant : on force role=superadmin (idempotent) et on backfill
            # les champs plan si absents. Le mot de passe n'est JAMAIS modifié ici.
            updates: dict = {}
            previous_role = existing.get("role")
            if previous_role != "superadmin":
                updates["role"] = "superadmin"
            if not existing.get("plan_tier"):
                updates["plan_tier"] = "premium"
                updates["plan_period"] = "yearly"
            if existing.get("plan") != "premium":
                updates["plan"] = "premium"

            if updates:
                await db.users.update_one({"_id": existing["_id"]}, {"$set": updates})
                if "role" in updates:
                    logger.info(
                        f"[seed-admin] PROMU : {existing.get('email')} "
                        f"role={previous_role!r} → 'superadmin' "
                        f"(backfill: {sorted(updates.keys())})"
                    )
                else:
                    logger.info(
                        f"[seed-admin] déjà superadmin : {existing.get('email')} "
                        f"(backfill plan : {sorted(updates.keys())})"
                    )
            else:
                logger.info(
                    f"[seed-admin] déjà superadmin : {existing.get('email')} — aucun changement"
                )

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
    default_promos = [
        {"code": "DECOUVERTE30", "label": "Essai 30 jours — 50 utilisations",
         "duration_days": 30, "max_uses": 50, "expires_at": None, "active": True},
    ]
    for promo in default_promos:
        existing = await db.promo_codes.find_one({"code": promo["code"]})
        if not existing:
            await db.promo_codes.insert_one({**promo, "used_count": 0, "redeemed_by": [],
                                             "created_at": datetime.now(timezone.utc).isoformat(),
                                             "created_by": "system"})
            logger.info(f"Promo seedé : {promo['code']}")

    await revoke_famille2026()

    # Seed 5 word-search grids on first boot (idempotent).
    from wordsearch_mistral import seed_grids_if_empty
    await seed_grids_if_empty()

    # Schedule all cron jobs (voir scheduler.py pour la matrice complète)
    start_scheduler()
    # Conseil du jour : 1 seul appel IA léger si absent (pas de subprocess)
    from daily_tips import daily_tip_job
    _asyncio.create_task(daily_tip_job())

    # NOTE : l'auto-seed au startup a été DÉSACTIVÉ car il lançait 2 subprocess
    # Mistral+Opus en même temps que le boot → pic mémoire → OOM du pod prod
    # → erreur Cloudflare 520. L'auto-seed reste disponible **à la demande**
    # via le bouton "Auto-seed toutes les catégories manquantes" dans
    # /app/admin/qa (endpoint POST /api/admin/qa/auto-seed).


@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()
    client.close()
