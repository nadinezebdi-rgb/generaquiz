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

import resend
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core import db, logger, FRONTEND_URL, RESEND_API_KEY, SENDER_EMAIL


def _today_key() -> str:
    """Same convention as routers.daily — Europe/Paris (UTC+1, no DST handling)."""
    now = datetime.now(timezone.utc) + timedelta(hours=1)
    return now.strftime("%Y-%m-%d")


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


def start_daily_scheduler() -> None:
    """Start the APScheduler job for morning emails (09:00 Europe/Paris)."""
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
    _scheduler.start()
    logger.info("[daily-email] scheduler démarré — envoi quotidien à 09:00 Europe/Paris")


def stop_daily_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
