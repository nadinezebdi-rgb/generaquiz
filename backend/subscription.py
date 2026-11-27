"""Abonnements récurrents Stripe : super promo de Noël, activation, résiliation, e-mails et synchronisation."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import resend
import stripe
from bson import ObjectId
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException

from core import db, logger, FRONTEND_URL, PACKAGES, RESEND_API_KEY, SENDER_EMAIL, STRIPE_API_KEY, get_current_user
from routers.family import family_subscription_fields

router = APIRouter(prefix="/subscription", tags=["subscription"])

PARIS = ZoneInfo("Europe/Paris")
PROMO_END = datetime(2026, 12, 31, 23, 59, 59, tzinfo=PARIS)
GRACE = timedelta(days=3)  # marge d'accès le temps que le prélèvement passe
TIER_NAME = {"solo": "Solo", "famille_v2": "Famille"}
SIMULATED = "sk_test_emergent" in STRIPE_API_KEY  # clé de test partagée : pas d'API abonnement


def promo_active(now: datetime | None = None) -> bool:
    return (now or datetime.now(timezone.utc)) <= PROMO_END


def check_package_sellable(package_id: str) -> dict:
    pkg = PACKAGES.get(package_id)
    if not pkg or pkg.get("legacy") or pkg.get("tier") == "gift":
        raise HTTPException(status_code=400, detail="Forfait invalide")
    # Les tarifs normaux sont toujours vendus ; le tarif de Noël seulement jusqu'au 31 décembre 2026.
    if pkg.get("promo") and not promo_active():
        raise HTTPException(status_code=400, detail="La super promo de Noël est terminée depuis le 31 décembre 2026.")
    return pkg


def eur(amount: float) -> str:
    return (f"{amount:.0f} €" if float(amount).is_integer() else f"{amount:.2f} €".replace(".", ","))


def fr_date(d: datetime) -> str:
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
              "septembre", "octobre", "novembre", "décembre"]
    d = d.astimezone(PARIS)
    return f"{d.day} {months[d.month - 1]} {d.year}"


def _stripe():
    stripe.api_key = STRIPE_API_KEY
    stripe.api_base = "https://integrations.emergentagent.com/stripe" if SIMULATED else "https://api.stripe.com"
    return stripe


def summary_text(pkg: dict) -> str:
    """Récapitulatif affiché avant le paiement (et rappelé dans Stripe)."""
    name = TIER_NAME[pkg["tier"]]
    cancel = "Résiliable à tout moment depuis Mon compte → Abonnement, en un clic."
    if pkg["period"] == "monthly":
        return (f"{name} mensuel : {eur(pkg['amount'])} aujourd'hui, puis {eur(pkg['amount'])} chaque mois "
                f"à la même date. Sans engagement, résiliable à tout moment depuis Mon compte → Abonnement, en un clic.")
    head = f"Super promo de Noël {name}" if pkg.get("promo") else f"{name} annuel"
    return (f"{head} : {eur(pkg['amount'])} aujourd'hui pour 12 mois, à compter de votre première connexion. "
            f"Ensuite : renouvellement automatique à {eur(pkg['renew_amount'])}/an. "
            f"Vous recevrez un e-mail de rappel 30 jours avant. {cancel}")


def create_checkout_session(pkg: dict, package_id: str, user: dict, origin: str) -> dict:
    s = _stripe()
    name = TIER_NAME[pkg["tier"]]
    interval = "month" if pkg["period"] == "monthly" else "year"
    recurring = {"price_data": {"currency": "eur", "unit_amount": round(pkg["renew_amount"] * 100),
                                "recurring": {"interval": interval},
                                "product_data": {"name": f"GénéraQuiz {name} — {'mensuel' if interval == 'month' else 'annuel'}"}},
                 "quantity": 1}
    kwargs = dict(mode="subscription", locale="fr", customer_email=user["email"],
                  success_url=f"{origin}/app/success?session_id={{CHECKOUT_SESSION_ID}}",
                  cancel_url=f"{origin}/app/pricing",
                  metadata={"user_id": str(user["_id"]), "package_id": package_id},
                  custom_text={"submit": {"message": summary_text(pkg)[:1000]}})
    if pkg.get("promo"):
        # 49 € / 79 € encaissés aujourd'hui, l'abonnement annuel normal ne démarre qu'au bout de 12 mois.
        first_renewal = datetime.now(timezone.utc) + relativedelta(years=1) + timedelta(hours=2)
        recurring["price_data"]["product_data"] = {
            "name": f"GénéraQuiz {name} annuel — {eur(pkg['renew_amount'])}/an à partir du {fr_date(first_renewal)}",
            "description": f"Prélevé seulement à partir du {fr_date(first_renewal)}, résiliable avant à tout moment."}
        kwargs["line_items"] = [recurring, {"price_data": {"currency": "eur", "unit_amount": round(pkg["amount"] * 100),
                                                           "product_data": {"name": f"Super promo de Noël {name} — 12 mois",
                                                                            "description": f"{eur(pkg['amount'])} payés aujourd'hui pour 12 mois d'accès"}},
                                            "quantity": 1}]
        kwargs["subscription_data"] = {"trial_end": int(first_renewal.timestamp()),
                                       "metadata": {"user_id": str(user["_id"]), "package_id": package_id}}
    else:
        kwargs["line_items"] = [recurring]
        kwargs["subscription_data"] = {"metadata": {"user_id": str(user["_id"]), "package_id": package_id}}
    return s.checkout.Session.create(**kwargs)


async def activate_from_session(session_id: str) -> None:
    """Idempotent : active l'abonnement une seule fois, puis envoie les e-mails."""
    tx = await db.payment_transactions.find_one({"session_id": session_id, "gift": {"$ne": True}})
    if not tx or tx.get("payment_status") == "paid":
        return
    pkg = PACKAGES.get(tx.get("package_id"), {})
    user = await db.users.find_one({"_id": ObjectId(tx["user_id"])})
    if not user or not pkg:
        logger.error(f"[subscription] activation impossible pour {session_id}")
        return
    sess = await asyncio.to_thread(_stripe().checkout.Session.retrieve, session_id)  # erreur → réessai au prochain appel
    sub_id, customer_id = sess.get("subscription"), sess.get("customer")
    if not sub_id and not SIMULATED:
        logger.error(f"[subscription] session {session_id} sans abonnement Stripe")
        return
    claimed = await db.payment_transactions.update_one(
        {"session_id": session_id, "payment_status": {"$ne": "paid"}},
        {"$set": {"payment_status": "paid", "status": "complete", "stripe_subscription_id": sub_id}})
    if not claimed.modified_count:
        return
    start = datetime.now(timezone.utc)
    renews_at = start + (relativedelta(months=1) if pkg["period"] == "monthly" else relativedelta(years=1))
    await db.users.update_one({"_id": user["_id"]}, {"$set": {
        "plan": "premium", "plan_tier": pkg["tier"], "plan_period": pkg["period"],
        "plan_package_id": tx["package_id"], "plan_started_at": start.isoformat(),
        "plan_renews_at": renews_at.isoformat(), "plan_expires_at": (renews_at + GRACE).isoformat(),
        "plan_auto_renew": True, "plan_cancel_at_period_end": False, "plan_renewal_amount": pkg["renew_amount"],
        "first_login_at": user.get("first_login_at") or start.isoformat(),
        "stripe_subscription_id": sub_id, "stripe_customer_id": customer_id,
        **family_subscription_fields(user, pkg["tier"], pkg.get("max_proches")),
    }})
    await send_confirmation_email(user, pkg, start, renews_at)
    if pkg["period"] == "yearly":
        await send_activation_email(user, start, renews_at)


async def cancel_subscription(user: dict) -> dict:
    if not user.get("plan_auto_renew"):
        raise HTTPException(status_code=400, detail="Aucun abonnement à renouvellement automatique")
    if user.get("plan_cancel_at_period_end"):
        return {"cancelled": True, "access_until": user.get("plan_renews_at")}
    sub_id = user.get("stripe_subscription_id")
    if not SIMULATED and not sub_id:
        raise HTTPException(status_code=409, detail="Abonnement introuvable chez notre prestataire de paiement : écrivez-nous via la page Contact, nous le résilions aussitôt.")
    if not SIMULATED:
        try:
            await asyncio.to_thread(_stripe().Subscription.modify, sub_id, cancel_at_period_end=True)
        except Exception as e:
            logger.error(f"[subscription] résiliation Stripe impossible pour {sub_id} : {e}")
            raise HTTPException(status_code=502, detail="La résiliation n'a pas pu être enregistrée. Réessayez dans un instant.")
    elif SIMULATED:
        logger.info(f"[subscription] résiliation simulée (clé de test partagée) pour {user['email']}")
    await db.users.update_one({"_id": user["_id"]}, {"$set": {
        "plan_cancel_at_period_end": True, "plan_cancelled_at": datetime.now(timezone.utc).isoformat(),
        "plan_expires_at": user.get("plan_renews_at") or user.get("plan_expires_at")}})
    return {"cancelled": True, "access_until": user.get("plan_renews_at")}


@router.post("/cancel")
async def cancel_endpoint(user: dict = Depends(get_current_user)) -> dict:
    return await cancel_subscription(user)


# -------------------------------------------------------------------- e-mails
def _mail(title: str, body: str) -> str:
    return (f"<div style='font-family:Arial,sans-serif;color:#1A2530;max-width:560px;margin:auto;font-size:16px;line-height:1.5'>"
            f"<h2 style='font-family:Georgia,serif;color:#1E3A5F'>{title}</h2>{body}"
            f"<p style='margin-top:28px'>À bientôt sur GénéraQuiz !</p></div>")


def _cancel_block() -> str:
    url = f"{FRONTEND_URL}/app/account#abonnement"
    return (f"<p>Vous pouvez résilier à tout moment, en un clic : "
            f"<a href='{url}' style='color:#E07A5F;font-weight:bold'>résilier mon abonnement</a>.</p>")


def _row(k: str, v: str) -> str:
    return f"<tr><td style='padding:6px 12px 6px 0;color:#1A2530'>{k}</td><td style='padding:6px 0'><strong>{v}</strong></td></tr>"


def confirmation_email(user: dict, pkg: dict, start: datetime, renews_at: datetime) -> tuple[str, str]:
    name = TIER_NAME[pkg["tier"]]
    offer = f"Super promo de Noël {name}" if pkg.get("promo") else f"{name} {'mensuel' if pkg['period'] == 'monthly' else 'annuel'}"
    if pkg["period"] == "monthly":
        period, renewal = "Mensuelle, sans engagement", f"{eur(pkg['renew_amount'])} le {fr_date(renews_at)}, puis chaque mois"
    else:
        period = "12 mois"
        renewal = f"Renouvellement automatique à {eur(pkg['renew_amount'])}/an le {fr_date(renews_at)}"
    rows = _row("Offre", offer) + _row("Montant payé", eur(pkg["amount"])) + _row("Périodicité", period)
    if pkg["period"] == "yearly":
        rows += _row("Début des 12 mois", fr_date(start))
    rows += _row("Prochain prélèvement", renewal)
    body = (f"<p>Bonjour {user.get('name') or ''},</p><p>Merci pour votre abonnement, il est actif dès maintenant.</p>"
            f"<table style='border-collapse:collapse;margin:12px 0'>{rows}</table>"
            f"{'<p>Vous recevrez un e-mail de rappel 30 jours avant le renouvellement.</p>' if pkg['period'] == 'yearly' else ''}"
            f"{_cancel_block()}")
    return f"Votre abonnement GénéraQuiz {name} est confirmé", _mail("Abonnement confirmé", body)


def activation_email(user: dict, start: datetime, end: datetime) -> tuple[str, str]:
    body = (f"<p>Bonjour {user.get('name') or ''},</p>"
            f"<p style='font-size:18px'>Vos 12 mois ont commencé le <strong>{fr_date(start)}</strong> "
            f"et se terminent le <strong>{fr_date(end)}</strong>.</p>"
            f"<p>Bonne découverte des quiz, du Livre de Vie et des jeux de mots !</p>"
            f"<p><a href='{FRONTEND_URL}/app' style='background:#E07A5F;color:#fff;padding:12px 24px;border-radius:999px;"
            f"text-decoration:none;font-weight:bold'>Commencer à jouer</a></p>")
    return "Vos 12 mois GénéraQuiz ont commencé", _mail("C'est parti pour 12 mois !", body)


def reminder_email(user: dict, renews_at: datetime, amount: float) -> tuple[str, str]:
    body = (f"<p>Bonjour {user.get('name') or ''},</p>"
            f"<p>Votre abonnement annuel GénéraQuiz se renouvelle automatiquement le <strong>{fr_date(renews_at)}</strong>.</p>"
            f"<p>Montant du prochain prélèvement : <strong>{eur(amount)}</strong> pour 12 mois.</p>"
            f"<p>Rien à faire pour continuer à jouer.</p>{_cancel_block()}")
    return f"Votre abonnement se renouvelle le {fr_date(renews_at)}", _mail("Rappel de renouvellement", body)


async def _send(to: str, subject: str, html: str) -> bool:
    if not RESEND_API_KEY:
        logger.warning(f"[subscription] RESEND_API_KEY absent — e-mail « {subject} » non envoyé")
        return False
    try:
        await asyncio.to_thread(resend.Emails.send, {"from": SENDER_EMAIL, "to": [to], "subject": subject, "html": html})
        return True
    except Exception as e:
        logger.warning(f"[subscription] e-mail « {subject} » non envoyé à {to} : {e}")
        return False


async def send_confirmation_email(user, pkg, start, renews_at):
    await _send(user["email"], *confirmation_email(user, pkg, start, renews_at))


async def send_activation_email(user, start, end):
    await _send(user["email"], *activation_email(user, start, end))


# ------------------------------------------------------------- tâches planifiées
async def send_renewal_reminders() -> dict:
    """Rappel 30 jours avant le renouvellement annuel (une seule fois par échéance)."""
    now = datetime.now(timezone.utc)
    sent = 0
    async for u in db.users.find({
        "plan_auto_renew": True, "plan_cancel_at_period_end": {"$ne": True}, "plan_period": "yearly",
        "plan_renews_at": {"$gte": (now + timedelta(days=30)).isoformat(), "$lt": (now + timedelta(days=31)).isoformat()},
    }):
        if u.get("renewal_reminder_sent_for") == u["plan_renews_at"]:
            continue
        renews_at = datetime.fromisoformat(u["plan_renews_at"])
        if await _send(u["email"], *reminder_email(u, renews_at, u.get("plan_renewal_amount") or 0)):
            await db.users.update_one({"_id": u["_id"]}, {"$set": {"renewal_reminder_sent_for": u["plan_renews_at"]}})
            sent += 1
    logger.info(f"[subscription] rappels J-30 envoyés : {sent}")
    return {"sent": sent}


def _period_end(sub) -> int | None:
    if sub.get("status") == "trialing" and sub.get("trial_end"):
        return sub["trial_end"]
    items = (sub.get("items") or {}).get("data") or []
    return sub.get("current_period_end") or (items[0].get("current_period_end") if items else None)


async def sync_renewals() -> dict:
    """Prolonge l'accès des abonnés dont Stripe a renouvelé l'abonnement."""
    if SIMULATED:
        return {"skipped": "clé de test partagée"}
    now = datetime.now(timezone.utc)
    renewed = ended = 0
    async for u in db.users.find({"plan_auto_renew": True, "plan_cancel_at_period_end": {"$ne": True},
                                  "stripe_subscription_id": {"$nin": [None, ""]},
                                  "plan_renews_at": {"$lte": (now + timedelta(hours=12)).isoformat()}}):
        try:
            sub = await asyncio.to_thread(_stripe().Subscription.retrieve, u["stripe_subscription_id"])
        except Exception as e:
            logger.warning(f"[subscription] lecture {u['stripe_subscription_id']} impossible : {e}")
            continue
        end = _period_end(sub)
        if sub.get("status") in ("active", "trialing") and end and end > now.timestamp():
            renews_at = datetime.fromtimestamp(end, timezone.utc)
            await db.users.update_one({"_id": u["_id"]}, {"$set": {
                "plan_renews_at": renews_at.isoformat(), "plan_expires_at": (renews_at + GRACE).isoformat()}})
            renewed += 1
        elif sub.get("status") in ("canceled", "unpaid", "incomplete_expired"):
            await db.users.update_one({"_id": u["_id"]}, {"$set": {"plan_auto_renew": False}})
            ended += 1
    logger.info(f"[subscription] synchro renouvellements : {renewed} prolongé(s), {ended} terminé(s)")
    return {"renewed": renewed, "ended": ended}
