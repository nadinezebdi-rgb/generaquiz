"""Morning Quiz du Jour email reminder.

Schedules a daily job at 09:00 Europe/Paris that sends an email to every user who:
  - has opted-in to daily emails (`daily_email_optin != false`, default true)
  - has NOT yet played today's quiz

The email is rendered with the user's current streak (🔥 N jours) and a CTA to play.
Resend is used as the transport.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

import resend
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core import db, logger, FRONTEND_URL, RESEND_API_KEY, SENDER_EMAIL

PARIS_TZ = ZoneInfo("Europe/Paris")

# Resend "test mode" sandbox = clé non vérifiée, seul l'email du propriétaire
# de compte peut recevoir des messages depuis onboarding@resend.dev. On détecte
# cela pour adapter le log et éviter de marquer un envoi comme échoué à tort.
RESEND_TEST_MODE = "onboarding@resend.dev" in SENDER_EMAIL


def _today_key() -> str:
    """Europe/Paris calendar day, DST-aware (CET/CEST)."""
    return datetime.now(PARIS_TZ).strftime("%Y-%m-%d")


def _build_morning_email_html(name: str, streak: int, play_url: str) -> str:
    streak_block = ""
    if streak >= 2:
        streak_block = f"""
        <tr><td style="padding:0 30px 10px 30px;text-align:center;">
          <div style="display:inline-block;background-color:#FCE7B6;border:2px solid #C9A227;color:#1A2530;font-weight:bold;font-size:18px;padding:10px 18px;border-radius:999px;">
            🔥 Série en cours : {streak} jours
          </div>
        </td></tr>"""
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Votre Quiz du Jour vous attend</title></head>
<body style="margin:0;padding:0;background-color:#F4F1DE;font-family:Arial,Helvetica,sans-serif;color:#1A2530;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F4F1DE;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background-color:#FFFFFF;border-radius:24px;border:2px solid #E8E2C9;overflow:hidden;">
        <tr><td style="background-color:#1E3A5F;padding:30px;text-align:center;">
          <div style="display:inline-block;background-color:#E07A5F;color:#FFFFFF;font-weight:bold;font-size:14px;padding:6px 14px;border-radius:999px;letter-spacing:1px;text-transform:uppercase;">GénéraQuiz</div>
          <h1 style="color:#FFFFFF;font-size:26px;margin:18px 0 6px 0;">Bonjour {name} ☀️</h1>
          <p style="color:#F4F1DE;margin:0;font-size:15px;">Le jeu qui rapproche les générations</p>
        </td></tr>
        {streak_block}
        <tr><td style="padding:30px 30px 10px 30px;">
          <h2 style="margin:0 0 14px 0;color:#1E3A5F;font-size:22px;">Votre Quiz du Jour vous attend !</h2>
          <p style="font-size:16px;line-height:1.6;margin:0 0 14px 0;">
            5 nouvelles questions, mêmes pour tous les joueurs, fraîches du matin. 
            {"Ne cassez pas votre série de " + str(streak) + " jours 🔥" if streak >= 2 else "Lancez votre série dès aujourd'hui."}
          </p>
        </td></tr>
        <tr><td style="padding:10px 30px 30px 30px;text-align:center;">
          <a href="{play_url}" style="display:inline-block;background-color:#E07A5F;color:#FFFFFF;font-weight:bold;font-size:17px;padding:14px 30px;border-radius:999px;text-decoration:none;">
            Jouer maintenant →
          </a>
        </td></tr>
        <tr><td style="background-color:#F4F1DE;padding:18px 30px;text-align:center;font-size:12px;color:#1E3A5F;">
          Vous recevez cet email car vous êtes inscrit·e à GénéraQuiz.<br/>
          <a href="{FRONTEND_URL}/app/account" style="color:#7A1F2B;">Gérer mes préférences email</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


async def _send_one(user: dict) -> bool:
    name = user.get("name") or user.get("email", "").split("@")[0]
    streak = int(user.get("streak_current") or 0)
    play_url = f"{FRONTEND_URL}/quiz-du-jour"
    html = _build_morning_email_html(name, streak, play_url)
    try:
        # resend.Emails.send is synchronous — run in a thread to keep the loop responsive
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [user["email"]],
            "subject": f"☀️ Votre Quiz du Jour vous attend{(f' (🔥 série de {streak} jours)' if streak >= 2 else '')}",
            "html": html,
        })
        return True
    except Exception as e:
        msg = str(e)
        if "testing" in msg.lower() or "verify a domain" in msg.lower():
            logger.warning(f"[daily-email] {user.get('email')} non envoyé — Resend en mode test : vérifiez le domaine SENDER_EMAIL sur resend.com/domains")
        else:
            logger.warning(f"[daily-email] échec pour {user.get('email')}: {e}")
        return False


async def send_morning_emails() -> dict:
    """Iterate eligible users and send the reminder. Returns a summary dict.

    Optimised: 1 query to get all users who already played today (instead of N queries),
    then filter in-memory while iterating opt-in users.
    """
    if not RESEND_API_KEY:
        logger.info("[daily-email] RESEND_API_KEY manquant — envoi sauté")
        return {"sent": 0, "skipped": 0, "reason": "no_resend_key"}

    today = _today_key()
    sent = 0
    skipped = 0
    failed = 0

    # Batch: get all user_ids who already played today (single Mongo query)
    played_user_ids: set[str] = set()
    async for att in db.daily_attempts.find({"date_key": today}, {"user_id": 1, "_id": 0}):
        played_user_ids.add(att["user_id"])

    # users opted-in (default true if field absent)
    cursor = db.users.find({
        "$or": [{"daily_email_optin": {"$ne": False}}, {"daily_email_optin": {"$exists": False}}],
    })
    async for user in cursor:
        if str(user["_id"]) in played_user_ids:
            skipped += 1
            continue
        ok = await _send_one(user)
        if ok:
            sent += 1
        else:
            failed += 1
        # Pace requests below Resend's 5 req/s rate limit
        await asyncio.sleep(0.25)

    logger.info(f"[daily-email] sent={sent} skipped={skipped} failed={failed}")
    return {"sent": sent, "skipped": skipped, "failed": failed, "date": today}


_scheduler: AsyncIOScheduler | None = None


def _build_expiration_email_html(name: str, expires_label: str, pricing_url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Votre Premium expire dans 7 jours</title></head>
<body style="margin:0;padding:0;background-color:#F4F1DE;font-family:Arial,Helvetica,sans-serif;color:#1A2530;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F4F1DE;padding:40px 20px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background-color:#FFFFFF;border-radius:24px;border:2px solid #E8E2C9;overflow:hidden;">
        <tr><td style="background-color:#1E3A5F;padding:30px;text-align:center;">
          <div style="display:inline-block;background-color:#F2CC8F;color:#1A2530;font-weight:bold;font-size:14px;padding:6px 14px;border-radius:999px;letter-spacing:1px;text-transform:uppercase;">GénéraQuiz · Premium</div>
          <h1 style="color:#FFFFFF;font-size:26px;margin:18px 0 6px 0;">Bonjour {name} 👋</h1>
        </td></tr>
        <tr><td style="padding:30px 30px 10px 30px;">
          <h2 style="margin:0 0 14px 0;color:#1E3A5F;font-size:22px;">Votre abonnement Premium expire bientôt</h2>
          <p style="font-size:16px;line-height:1.6;margin:0 0 14px 0;">
            Petit rappel amical : votre accès Premium prend fin le <strong>{expires_label}</strong> (dans environ 7 jours).
          </p>
          <p style="font-size:16px;line-height:1.6;margin:0 0 14px 0;">
            En renouvelant dès maintenant, vous gardez sans interruption :
          </p>
          <ul style="font-size:15px;line-height:1.8;margin:0 0 18px 22px;color:#334155;">
            <li>📚 Accès aux <strong>800 questions</strong> régénérées chaque nuit</li>
            <li>🎯 Quiz de 30 questions par catégorie (vs 5 en gratuit)</li>
            <li>👨‍👩‍👧‍👦 Création illimitée de <strong>Défis Famille</strong></li>
            <li>🔥 Sauvegarde de votre série en cours</li>
          </ul>
        </td></tr>
        <tr><td style="padding:10px 30px 30px 30px;text-align:center;">
          <a href="{pricing_url}" style="display:inline-block;background-color:#E07A5F;color:#FFFFFF;font-weight:bold;font-size:17px;padding:14px 30px;border-radius:999px;text-decoration:none;">
            Renouveler mon Premium →
          </a>
          <p style="font-size:13px;color:#64748B;margin:14px 0 0 0;">
            Sans engagement. Vous pouvez annuler à tout moment.
          </p>
        </td></tr>
        <tr><td style="background-color:#F4F1DE;padding:18px 30px;text-align:center;font-size:12px;color:#1E3A5F;">
          Merci de votre fidélité à GénéraQuiz 🧡<br/>
          <a href="{FRONTEND_URL}/app/account" style="color:#7A1F2B;">Gérer mon abonnement</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


async def _send_expiration_one(user: dict, expires_at: datetime) -> bool:
    name = user.get("name") or user.get("email", "").split("@")[0]
    expires_label = expires_at.astimezone(PARIS_TZ).strftime("%d %B %Y")
    pricing_url = f"{FRONTEND_URL}/app/pricing"
    html = _build_expiration_email_html(name, expires_label, pricing_url)
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL,
            "to": [user["email"]],
            "subject": "⏰ Votre Premium GénéraQuiz expire dans 7 jours",
            "html": html,
        })
        return True
    except Exception as e:
        logger.warning(f"[expiration-email] échec pour {user.get('email')}: {e}")
        return False


async def send_expiration_emails() -> dict:
    """Find premium users whose plan_expires_at falls in [now+7d, now+8d]
    and send a single J-7 renewal reminder.

    Idempotent: each user receives at most one J-7 email per expiration cycle —
    we mark `expiration_email_sent_for` with the iso expiration date and skip
    users whose stored marker matches the current upcoming expiration.
    """
    if not RESEND_API_KEY:
        logger.info("[expiration-email] RESEND_API_KEY manquant — envoi sauté")
        return {"sent": 0, "skipped": 0, "reason": "no_resend_key"}

    now = datetime.now(timezone.utc)
    window_start = now + timedelta(days=7)
    window_end = now + timedelta(days=8)
    window_start_iso = window_start.isoformat()
    window_end_iso = window_end.isoformat()

    sent = 0
    skipped = 0
    failed = 0

    cursor = db.users.find({
        "plan": "premium",
        "plan_expires_at": {"$gte": window_start_iso, "$lt": window_end_iso},
    })
    async for user in cursor:
        expires_at_raw = user.get("plan_expires_at")
        if not expires_at_raw:
            continue
        # Skip lifetime accounts (year > 2090 → ~+3650 days set at admin seed)
        try:
            expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
        except Exception:
            continue
        if expires_at.year > 2090:
            skipped += 1
            continue
        # Idempotency marker: don't re-send if we already sent for this exact expiration
        if user.get("expiration_email_sent_for") == expires_at_raw:
            skipped += 1
            continue
        ok = await _send_expiration_one(user, expires_at)
        if ok:
            sent += 1
            await db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"expiration_email_sent_for": expires_at_raw}},
            )
        else:
            failed += 1
        await asyncio.sleep(0.25)

    logger.info(f"[expiration-email] sent={sent} skipped={skipped} failed={failed}")
    return {"sent": sent, "skipped": skipped, "failed": failed}



def start_daily_scheduler() -> None:
    """Start the APScheduler jobs:
    - Daily morning emails at 09:00 Europe/Paris
    - Weekly league settlement at Monday 00:05 Europe/Paris
    """
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="Europe/Paris")
    _scheduler.add_job(
        send_morning_emails,
        CronTrigger(hour=9, minute=0, timezone="Europe/Paris"),
        id="daily_quiz_email",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    # Lazy import to avoid circular imports at module load
    from routers.gamification import settle_finished_week  # noqa: WPS433
    from mistral_client import regenerate_all as _mistral_regen  # noqa: WPS433
    _scheduler.add_job(
        settle_finished_week,
        CronTrigger(day_of_week="mon", hour=0, minute=5, timezone="Europe/Paris"),
        id="leagues_weekly_settle",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.add_job(
        _mistral_regen,
        CronTrigger(hour=3, minute=0, timezone="Europe/Paris"),
        id="mistral_regenerate_all",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.add_job(
        send_expiration_emails,
        CronTrigger(hour=10, minute=0, timezone="Europe/Paris"),
        id="premium_expiration_email_j7",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info(
        "[scheduler] démarré — email quotidien 09:00 Paris + régénération Mistral 03:00 Paris + clôture ligues lundi 00:05 Paris + relance expiration J-7 10:00 Paris"
    )


def stop_daily_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
